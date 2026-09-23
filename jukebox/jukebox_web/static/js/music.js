(function ($) {
    "use strict";

    const gettext = typeof window.gettext === "function" ? window.gettext : (text) => text;

    const PAGE_SIZE = 30;
    const PING_INTERVAL = 60000;
    const STATIC_URL = document.body.dataset.staticUrl || "/static/";

    const HTML_ESCAPES = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    };

    // everything rendered into the page comes from ID3 tags or social
    // network profiles, never insert it without escaping
    function escapeHtml(value) {
        return String(value === null || value === undefined ? "" : value)
            .replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
    }

    function image(name) {
        return STATIC_URL + "img/" + name;
    }

    function icon(file, cls, id, label) {
        return "<img src=\"" + image(file) + "\" class=\"" + cls + "\" data-id=\"" + escapeHtml(id) +
            "\" alt=\"" + escapeHtml(label) + "\" title=\"" + escapeHtml(label) + "\" />";
    }

    function emptyCell() {
        return "<td>&#160;</td>";
    }

    function filterCell(cls, value, label) {
        if (value === null || value === undefined) {
            return emptyCell();
        }
        return "<td class=\"filter " + cls + "\" data-value=\"" + escapeHtml(value) + "\">" +
            escapeHtml(label) + "</td>";
    }

    function formatLength(length) {
        if (length === null || length === undefined) {
            return "";
        }
        const seconds = length % 60;
        return Math.floor(length / 60) + ":" + (seconds < 10 ? "0" : "") + seconds;
    }

    const cells = {
        title: (item) => filterCell("search_title", item.title, item.title),
        artist: (item) => filterCell("filter_artist", item.artist.id, item.artist.name),
        album: (item) => filterCell("filter_album", item.album.id, item.album.title),
        genre: (item) => filterCell("filter_genre", item.genre.id, item.genre.name),
        year: (item) => filterCell("filter_year", item.year, item.year),
        length: (item) => "<td>" + escapeHtml(formatLength(item.length)) + "</td>",
        created: (item) => "<td>" + escapeHtml(item.created) + "</td>",
        votes: (item) => {
            let html = "<td class=\"voteCount\">";
            if (item.votes > 0) {
                if (item.users.length === item.votes) {
                    html += "<div class=\"voteTooltip\"><ul>";
                    item.users.forEach((user) => {
                        html += "<li>" + escapeHtml(user.name) + "</li>";
                    });
                    html += "</ul></div>";
                }
                html += "<span class=\"count\">" + escapeHtml(item.votes) + "</span>";
            }
            else {
                html += escapeHtml(gettext("Autoplay"));
            }
            return html + "</td>";
        }
    };

    function column(label, cls, sort, cell) {
        return {label: label, cls: cls, sort: sort, cell: cell};
    }

    // columns shown for each list type returned by the API
    const LISTS = {
        "queue": {
            rowClass: "row_queue",
            voteLabel: gettext("Support vote"),
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist),
                column(gettext("Album"), "favourite_album", "album", cells.album),
                column(gettext("Votes"), "favourite_genre", "votes", cells.votes),
                column(gettext("First voted"), "favourite_added", "created", cells.created)
            ]
        },
        "history": {
            rowClass: "row_history",
            voteLabel: gettext("Vote to play"),
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist),
                column(gettext("Album"), "favourite_album", "album", cells.album),
                column(gettext("Votes"), "favourite_genre", null, cells.votes),
                column(gettext("Date added"), "favourite_added", "created", cells.created)
            ]
        },
        "favourites": {
            rowClass: "row_favourites",
            voteLabel: gettext("Vote to play"),
            alwaysFavourite: true,
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist),
                column(gettext("Album"), "favourite_album", "album", cells.album),
                column(gettext("Genre"), "favourite_genre", "genre", cells.genre),
                column(gettext("Date added"), "favourite_added", "created", cells.created)
            ]
        },
        "songs": {
            rowClass: "row_songs",
            voteLabel: gettext("Vote to play"),
            columns: [
                column(gettext("Title"), "song_title", "title", cells.title),
                column(gettext("Artist"), "song_artist", "artist", cells.artist),
                column(gettext("Album"), "song_album", "album", cells.album),
                column(gettext("Genre"), "song_genre", "genre", cells.genre),
                column(gettext("Year"), "song_year", "year", cells.year),
                column(gettext("Length"), "song_length", "length", cells.length)
            ]
        },
        "artists": {
            rowClass: "row_artists",
            columns: [
                column(gettext("Name"), "name", "artist",
                    (item) => filterCell("filter_artist", item.id, item.artist))
            ]
        },
        "albums": {
            rowClass: "row_albums",
            columns: [
                column(gettext("Title"), "album_title", "album",
                    (item) => filterCell("filter_album", item.id, item.album))
            ]
        },
        "genres": {
            rowClass: "row_genres",
            columns: [
                column(gettext("Name"), "name", "genre",
                    (item) => filterCell("filter_genre", item.id, item.genre))
            ]
        },
        "years": {
            rowClass: "row_years",
            columns: [
                column(gettext("Year"), "year", "year",
                    (item) => filterCell("filter_year", item.year, item.year))
            ]
        }
    };
    LISTS["history/my"] = LISTS.history;

    const Music = {
        url: null,
        pageNum: 1,
        hasNextPage: false,
        loading: false,
        generation: 0,
        options: {},
        searchOptions: {},
        remaining: 0,
        currentSongTimer: null,

        init: function () {
            $.ajaxSetup({
                type: "GET",
                cache: false,
                dataType: "json",
                headers: {
                    "X-CSRFToken": $("#csrf_token input[name=\"csrfmiddlewaretoken\"]").val()
                }
            });

            // session expired (e.g. after standby), the page redirects to the login
            $(document).on("ajaxError", (event, xhr) => {
                if (xhr.status === 401 || xhr.status === 403) {
                    window.location.reload();
                }
            });

            $(".loadList").on("click", function () {
                Music.options = {};
                Music.setActiveMenu($(this));
                Music.loadList($(this).attr("href"));
                return false;
            });

            Music.initSearch();
            Music.initMenus();
            Music.initList();

            $(window).on("scroll", Music.loadOnScroll);

            Music.getCurrentSong();
            Music.ping();
            Music.loadList("/api/v1/queue");
            Music.setActiveMenu($("#sidebar a.loadQueue"));
        },

        showSongs: function (options) {
            Music.options = options;
            Music.loadList("/api/v1/songs");
            Music.setActiveMenu($("#sidebar a.loadSongs"));
        },

        initSearch: function () {
            $("#searchform").on("submit", () => {
                Music.showSongs({"search_term": $("input.searchterm").val()});
                return false;
            });
            $("#searchform span.searchsubmit").on("click", () => {
                $("#searchform").trigger("submit");
                return false;
            });

            const submitDetails = () => {
                Music.showSongs(Music.getSearchOptions());
                Music.toggleSearchDetails(false);
                return false;
            };
            $("#searchdetailsform").on("submit", submitDetails);
            $("#searchdetailsform span.searchsubmit").on("click", submitDetails);
            // not every browser submits a form without visible submit button
            $("#search_title, #search_artist, #search_album").on("keydown", (event) => {
                if (event.key === "Enter") {
                    return submitDetails();
                }
            });
            $("#searchdetailsform span.searchreset").on("click", () => {
                Music.resetSearchDetails();
                return false;
            });

            $("#searchoptions").on("click", () => {
                Music.toggleSearchDetails(!$("#searchdetails").is(":visible"));
            });
        },

        toggleSearchDetails: function (show) {
            $(document).off("click.search");
            if (!show) {
                $("#searchdetails").hide();
                return;
            }

            // fill form by current search options
            Music.resetSearchDetails();
            const search = Music.searchOptions;
            const unbracket = (value) => String(value).replace(/^\((.*)\)$/, "$1");
            if (search.title) {
                $("#search_title").val(unbracket(search.title));
            }
            if (search.artist) {
                $("#search_artist").val(unbracket(search.artist));
            }
            if (search.album) {
                $("#search_album").val(unbracket(search.album));
            }
            if (search.genre_id) {
                $("#search_genre").val(search.genre_id);
            }
            if (search.year) {
                $("#search_year").val(search.year);
            }

            $("#searchdetails").show();
            $(document).on("click.search", (event) => {
                if ($(event.target).closest("#searchdetails, #searchoptions").length === 0) {
                    Music.toggleSearchDetails(false);
                }
            });
        },

        resetSearchDetails: function () {
            $("#search_title, #search_artist, #search_album, #search_genre, #search_year").val("");
        },

        initMenus: function () {
            $("#profile").on("click", () => {
                $(document).off("click.account");
                if ($("#accountoptions").is(":visible")) {
                    $("#accountoptions").hide();
                    return;
                }

                $("#accountoptions").show();
                $(document).on("click.account", (event) => {
                    if ($(event.target).closest("#accountoptions, #profile").length === 0) {
                        $(document).off("click.account");
                        $("#accountoptions").hide();
                    }
                });
            });
        },

        initList: function () {
            const main = $("#main");

            main.on("click", "table.list td.filter", function () {
                const cell = $(this);
                const value = cell.attr("data-value");
                const filters = {
                    filter_artist: "filter_artist_id",
                    filter_album: "filter_album_id",
                    filter_genre: "filter_genre",
                    filter_year: "filter_year",
                    search_title: "search_title"
                };
                const options = {};
                $.each(filters, (cls, option) => {
                    if (cell.hasClass(cls)) {
                        options[option] = value;
                    }
                });
                Music.showSongs(options);
                return false;
            });

            main.on("click", "table.list th[data-sort]", function () {
                Music.options.order_direction = $(this).hasClass("sort_asc") ? "desc" : "asc";
                Music.options.order_by = $(this).attr("data-sort");
                Music.loadList(Music.url);
                return false;
            });

            main.on("click", "table.list img.queue_add", function () {
                $.ajax({
                    url: "/api/v1/queue",
                    type: "POST",
                    data: {"id": $(this).attr("data-id")}
                }).done((data) => {
                    const items = $("img.queue_add[data-id=\"" + data.id + "\"]");
                    Music.setIcon(items, "queue_active.png", "queue_add", "queue_remove",
                        gettext("Revoke vote"));
                    items.closest("tr").find(".voteCount .count").text(data.count);
                });
                return false;
            });

            main.on("click", "table.list img.queue_remove", function () {
                const inQueue = $(this).closest("tr.row_queue").length > 0;
                $.ajax({
                    url: "/api/v1/queue/" + encodeURIComponent($(this).attr("data-id")),
                    type: "DELETE"
                }).done((data) => {
                    const items = $("img.queue_remove[data-id=\"" + data.id + "\"]");
                    if (inQueue && data.count === 0) {
                        items.closest("tr").fadeOut(1000, function () {
                            $(this).remove();
                        });
                        return;
                    }
                    Music.setIcon(items, "queue.png", "queue_remove", "queue_add",
                        inQueue ? gettext("Support vote") : gettext("Vote to play"));
                    items.closest("tr").find(".voteCount .count").text(data.count);
                });
                return false;
            });

            main.on("click", "table.list img.favourite_add", function () {
                $.ajax({
                    url: "/api/v1/favourites",
                    type: "POST",
                    data: {"id": $(this).attr("data-id")}
                }).done((data) => {
                    Music.setIcon($("img.favourite_add[data-id=\"" + data.id + "\"]"),
                        "favourite_active.png", "favourite_add", "favourite_remove",
                        gettext("Remove from favourites"));
                });
                return false;
            });

            main.on("click", "table.list img.favourite_remove", function () {
                const inFavourites = $(this).closest("tr.row_favourites").length > 0;
                $.ajax({
                    url: "/api/v1/favourites/" + encodeURIComponent($(this).attr("data-id")),
                    type: "DELETE"
                }).done((data) => {
                    const items = $("img.favourite_remove[data-id=\"" + data.id + "\"]");
                    if (inFavourites) {
                        items.closest("tr").fadeOut(1000, function () {
                            $(this).remove();
                        });
                        return;
                    }
                    Music.setIcon(items, "favourite.png", "favourite_remove", "favourite_add",
                        gettext("Add to favourites"));
                });
                return false;
            });

            main.on("mouseenter", "td.voteCount", function () {
                const offset = $(this).offset();
                $(this).find("div.voteTooltip").css({
                    left: offset.left - $(window).scrollLeft() + 50,
                    top: offset.top - $(window).scrollTop() + 10
                }).show();
            });
            main.on("mouseleave", "td.voteCount", function () {
                $(this).find("div.voteTooltip").hide();
            });
        },

        setIcon: function (items, file, removeClass, addClass, label) {
            items.attr({src: image(file), alt: label, title: label})
                .removeClass(removeClass)
                .addClass(addClass);
        },

        ping: function () {
            $.ajax({url: "/api/v1/ping"}).always(() => {
                setTimeout(Music.ping, PING_INTERVAL);
            });
        },

        getCurrentSong: function () {
            clearTimeout(Music.currentSongTimer);
            $.ajax({url: "/api/v1/songs/current"}).done((data) => {
                if ("id" in data) {
                    $("#currentSong strong").show();
                    $("#currentSong span.songTitle").text(data.artist.name + " - " + data.title);
                    Music.remaining = data.remaining;
                    Music.updateTimeLeft();
                }
                else {
                    $("#currentSong strong").hide();
                    Music.currentSongTimer = setTimeout(Music.getCurrentSong, 10000);
                }
            }).fail(() => {
                Music.currentSongTimer = setTimeout(Music.getCurrentSong, 10000);
            });
        },

        updateTimeLeft: function () {
            const element = $("#currentSong span.timeRemaining");
            if (Music.remaining <= 0) {
                // song is over, poll quickly until the player picked the next one
                element.hide();
                Music.currentSongTimer = setTimeout(
                    Music.getCurrentSong, Music.remaining > -30 ? 2000 : 10000);
                return;
            }

            element.text("(" + formatLength(Music.remaining) + ")").show();
            Music.remaining--;
            Music.currentSongTimer = setTimeout(Music.updateTimeLeft, 1000);
        },

        getSearchOptions: function () {
            const options = {};
            const fields = {
                search_title: "#search_title",
                search_artist: "#search_artist",
                search_album: "#search_album",
                filter_genre: "#search_genre",
                filter_year: "#search_year"
            };
            $.each(fields, (option, selector) => {
                const value = $(selector).val();
                if (value) {
                    options[option] = value;
                }
            });
            return options;
        },

        setActiveMenu: function (item) {
            $("#sidebar li").removeClass("active");
            item.closest("li").addClass("active");
        },

        loadList: function (url) {
            const generation = ++Music.generation;
            Music.url = url;
            Music.pageNum = 1;
            Music.hasNextPage = false;
            Music.loading = true;
            Music.searchOptions = {};
            Music.resetSearchDetails();

            Music.options.page = Music.pageNum;
            Music.options.count = PAGE_SIZE;

            $.ajax({url: url, data: Music.options}).done((data) => {
                if (generation !== Music.generation) {
                    return;
                }
                $(window).scrollTop(0);

                Music.hasNextPage = data.hasNextPage;
                if (data.itemList.length > 0) {
                    $("#main").html(Music.renderTable(data));
                    $("#main table.list tbody").append(Music.renderData(data));
                }
                else {
                    $("#main").html(
                        "<div class=\"noContent\">" + escapeHtml(gettext("No data found")) + "</div>");
                }

                // set search term - don't iterate to get correct order
                Music.searchOptions = data.search;
                const terms = [];
                ["title", "artist", "album", "genre", "year"].forEach((key) => {
                    if (data.search[key]) {
                        terms.push(key + ":" + data.search[key]);
                    }
                });
                if (data.search.term) {
                    terms.push(data.search.term);
                }
                $("input.searchterm").val(terms.join(" "));
            }).always(() => {
                if (generation === Music.generation) {
                    Music.loading = false;
                    Music.loadOnScroll();
                }
            });
        },

        loadOnScroll: function () {
            const scrolled = $(window).scrollTop() + $(window).height();
            if (!Music.loading && Music.hasNextPage && scrolled > $(document).height() * 0.8) {
                Music.loadNextPage();
            }
        },

        loadNextPage: function () {
            const generation = Music.generation;
            Music.loading = true;
            Music.pageNum++;
            Music.options.page = Music.pageNum;

            $.ajax({url: Music.url, data: Music.options}).done((data) => {
                if (generation !== Music.generation) {
                    return;
                }
                Music.hasNextPage = data.hasNextPage;
                $("#main table.list tbody").append(Music.renderData(data));
            }).always(() => {
                if (generation === Music.generation) {
                    Music.loading = false;
                    // keep loading until the page is filled
                    Music.loadOnScroll();
                }
            });
        },

        getOrderClass: function (field, data) {
            const order = data.order.find((item) => item.field === field);
            if (order && (order.direction === "asc" || order.direction === "desc")) {
                return " sort_" + order.direction;
            }
            return "";
        },

        renderTable: function (data) {
            const list = LISTS[data.type];
            let html = "<table class=\"list\"><thead><tr>";
            if (list.voteLabel) {
                html += "<th class=\"options\">&#160;</th>";
            }
            list.columns.forEach((col) => {
                if (col.sort) {
                    html += "<th class=\"" + col.cls + " sort_" + col.sort +
                        Music.getOrderClass(col.sort, data) + "\" data-sort=\"" + col.sort + "\">";
                }
                else {
                    html += "<th class=\"" + col.cls + "\">";
                }
                html += escapeHtml(col.label) + "</th>";
            });
            return html + "</tr></thead><tbody></tbody></table>";
        },

        renderData: function (data) {
            const list = LISTS[data.type];
            let html = "";
            data.itemList.forEach((item) => {
                html += "<tr class=\"" + list.rowClass + "\">";
                if (list.voteLabel) {
                    html += "<td>";
                    html += item.queued
                        ? icon("queue_active.png", "queue_remove", item.id, gettext("Revoke vote"))
                        : icon("queue.png", "queue_add", item.id, list.voteLabel);
                    html += item.favourite || list.alwaysFavourite
                        ? icon("favourite_active.png", "favourite_remove", item.id,
                            gettext("Remove from favourites"))
                        : icon("favourite.png", "favourite_add", item.id,
                            gettext("Add to favourites"));
                    html += "</td>";
                }
                list.columns.forEach((col) => {
                    html += col.cell(item);
                });
                html += "</tr>";
            });
            return html;
        }
    };

    window.Music = Music;
    $(Music.init);
}(jQuery));
