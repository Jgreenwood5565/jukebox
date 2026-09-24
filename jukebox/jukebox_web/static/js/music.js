(function ($) {
    "use strict";

    const gettext = typeof window.gettext === "function" ? window.gettext : (text) => text;

    const PAGE_SIZE = 30;
    const PING_INTERVAL = 60000;

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

    const ICONS = {
        vote: "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M12 19V5M5 12l7-7 7 7\"/></svg>",
        favourite: "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M12 20.5s-8-4.7-8-10.6" +
            "A4.4 4.4 0 0 1 12 7.3a4.4 4.4 0 0 1 8 2.6c0 5.9-8 10.6-8 10.6z\"/></svg>",
        empty: "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M9 18V5l12-2v13\"/>" +
            "<circle cx=\"6\" cy=\"18\" r=\"3\"/><circle cx=\"18\" cy=\"16\" r=\"3\"/></svg>"
    };

    // round button toggling a vote or favourite, "active" when set
    function toggleButton(kind, id, active, label) {
        return "<button type=\"button\" class=\"toggle " + kind + (active ? " active" : "") +
            "\" data-id=\"" + escapeHtml(id) + "\" aria-pressed=\"" + active + "\" title=\"" +
            escapeHtml(label) + "\" aria-label=\"" + escapeHtml(label) + "\">" + ICONS[kind] +
            "</button>";
    }

    function setToggle(items, active, label) {
        items.toggleClass("active", active)
            .attr({"aria-pressed": String(active), "title": label, "aria-label": label});
    }

    function emptyCell() {
        return "<td>&#160;</td>";
    }

    function filterCell(cls, value, label) {
        if (value === null || value === undefined) {
            return emptyCell();
        }
        return "<td class=\"filter " + cls + "\" data-value=\"" + escapeHtml(value) + "\" title=\"" +
            escapeHtml(label) + "\">" + escapeHtml(label) + "</td>";
    }

    function formatLength(length) {
        if (length === null || length === undefined) {
            return "";
        }
        length = Math.max(Math.floor(length), 0);
        const seconds = length % 60;
        return Math.floor(length / 60) + ":" + (seconds < 10 ? "0" : "") + seconds;
    }

    function votePill(item) {
        if (item.votes === 0) {
            return "<span class=\"votePill autoplay\">" + escapeHtml(gettext("Autoplay")) + "</span>";
        }
        return "<span class=\"votePill\">" + ICONS.vote + "<span class=\"count\">" +
            escapeHtml(item.votes) + "</span></span>";
    }

    const cells = {
        // small screens drop the artist column and show it below the title
        title: (item) => "<td class=\"filter search_title\" data-value=\"" + escapeHtml(item.title) +
            "\" title=\"" + escapeHtml(item.title) + "\"><span class=\"primary\">" +
            escapeHtml(item.title) + "</span><span class=\"subline\">" +
            escapeHtml(item.artist.name) + "</span></td>",
        artist: (item) => filterCell("filter_artist", item.artist.id, item.artist.name),
        album: (item) => filterCell("filter_album", item.album.id, item.album.title),
        genre: (item) => filterCell("filter_genre", item.genre.id, item.genre.name),
        year: (item) => filterCell("filter_year", item.year, item.year),
        length: (item) => "<td class=\"muted\">" + escapeHtml(formatLength(item.length)) + "</td>",
        created: (item) => "<td class=\"muted\">" + escapeHtml(item.created) + "</td>",
        votes: (item) => {
            let html = "<td class=\"voteCount\">";
            if (item.votes > 0 && item.users.length === item.votes) {
                html += "<div class=\"voteTooltip\"><ul>";
                item.users.forEach((user) => {
                    html += "<li>" + escapeHtml(user.name) + "</li>";
                });
                html += "</ul></div>";
            }
            return html + votePill(item) + "</td>";
        }
    };

    // "hide" names the screen size below which the column is left out
    function column(label, cls, sort, cell, hide) {
        return {label: label, cls: cls, sort: sort, cell: cell, hide: hide || null};
    }

    // columns shown for each list type returned by the API
    const LISTS = {
        "queue": {
            rowClass: "row_queue",
            voteLabel: gettext("Support vote"),
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist, "md"),
                column(gettext("Album"), "favourite_album", "album", cells.album, "md"),
                column(gettext("Votes"), "favourite_genre", "votes", cells.votes),
                column(gettext("First voted"), "favourite_added", "created", cells.created, "lg")
            ]
        },
        "history": {
            rowClass: "row_history",
            voteLabel: gettext("Vote to play"),
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist, "md"),
                column(gettext("Album"), "favourite_album", "album", cells.album, "md"),
                column(gettext("Votes"), "favourite_genre", null, cells.votes, "md"),
                column(gettext("Date added"), "favourite_added", "created", cells.created, "lg")
            ]
        },
        "favourites": {
            rowClass: "row_favourites",
            voteLabel: gettext("Vote to play"),
            alwaysFavourite: true,
            columns: [
                column(gettext("Title"), "favourite_title", "title", cells.title),
                column(gettext("Artist"), "favourite_artist", "artist", cells.artist, "md"),
                column(gettext("Album"), "favourite_album", "album", cells.album, "md"),
                column(gettext("Genre"), "favourite_genre", "genre", cells.genre, "md"),
                column(gettext("Date added"), "favourite_added", "created", cells.created, "lg")
            ]
        },
        "songs": {
            rowClass: "row_songs",
            voteLabel: gettext("Vote to play"),
            columns: [
                column(gettext("Title"), "song_title", "title", cells.title),
                column(gettext("Artist"), "song_artist", "artist", cells.artist, "md"),
                column(gettext("Album"), "song_album", "album", cells.album, "md"),
                column(gettext("Genre"), "song_genre", "genre", cells.genre, "lg"),
                column(gettext("Year"), "song_year", "year", cells.year, "md"),
                column(gettext("Length"), "song_length", "length", cells.length, "md")
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

    const POLL_INTERVAL = 10000;
    // a listener lagging behind by up to this many seconds hears a new song
    // from its start instead of jumping into it
    const START_TOLERANCE = 10;
    // seconds of slack when telling a finished song from a skipped one
    const END_SLACK = 3;
    const VOLUME_KEY = "jukebox.volume";

    // storage is unavailable in some private windows
    function storageGet(key) {
        try {
            return window.localStorage.getItem(key);
        }
        catch (error) {
            return null;
        }
    }

    function storageSet(key, value) {
        try {
            window.localStorage.setItem(key, value);
        }
        catch (error) {
            // the volume just isn't remembered
        }
    }

    // plays the song on air, the server decides what that is and when it's over
    const Player = {
        audio: null,
        listening: false,
        historyId: null,
        current: null,
        fetched: 0,
        // seconds this browser plays behind the server clock
        lag: 0,
        pollTimer: null,

        init: function () {
            if ($("#listen").length === 0) {
                return;
            }

            const audio = new Audio();
            audio.preload = "auto";
            audio.addEventListener("ended", () => {
                Music.getCurrentSong();
            });
            audio.addEventListener("error", () => {
                // e.g. the file is gone, the next poll tries again
                if (Player.listening) {
                    Player.historyId = null;
                }
            });
            Player.audio = audio;

            const volume = parseFloat(storageGet(VOLUME_KEY));
            if (volume >= 0 && volume <= 1) {
                audio.volume = volume;
                $("#volume").val(volume);
            }
            $("#volume").on("input", function () {
                audio.volume = this.value;
                storageSet(VOLUME_KEY, this.value);
            });

            $("#listen").on("click", () => {
                if (Player.listening) {
                    Player.stop();
                }
                else {
                    Player.start();
                }
            });

            if ("mediaSession" in navigator) {
                navigator.mediaSession.setActionHandler("play", Player.start);
                navigator.mediaSession.setActionHandler("pause", Player.stop);
            }

            Player.setButton();
        },

        start: function () {
            Player.listening = true;
            Player.historyId = null;
            Player.setButton();
            // start within the click, some browsers only allow audio then
            Player.sync();
            Player.poll();
        },

        stop: function () {
            Player.listening = false;
            Player.historyId = null;
            clearTimeout(Player.pollTimer);
            Player.audio.pause();
            Player.audio.removeAttribute("src");
            Player.audio.load();
            Player.setButton();
        },

        // skips by other listeners only show up when asking
        poll: function () {
            clearTimeout(Player.pollTimer);
            if (!Player.listening) {
                return;
            }
            Music.getCurrentSong();
            Player.pollTimer = setTimeout(Player.poll, POLL_INTERVAL);
        },

        // called with every response of /api/v1/songs/current
        receive: function (data) {
            Player.current = data;
            Player.fetched = Date.now();
            if (Player.listening && data.historyId === Player.historyId && !Player.audio.paused) {
                Player.lag = Math.max(data.position - Player.audio.currentTime, 0);
            }
            Player.sync();
        },

        sync: function () {
            const data = Player.current;
            if (!Player.listening || !data || !("historyId" in data) ||
                data.historyId === Player.historyId) {
                return;
            }

            // if the song here simply ended on the server, what's left of it
            // is about the lag, anything more means it was skipped
            const audio = Player.audio;
            const left = audio.duration - audio.currentTime;
            if (Player.historyId !== null && !audio.paused && !audio.ended &&
                left + data.position < Player.lag + END_SLACK) {
                // "ended" syncs again
                return;
            }

            Player.play(data);
        },

        play: function (data) {
            let position = data.position + (Date.now() - Player.fetched) / 1000;
            if (position < START_TOLERANCE) {
                position = 0;
            }

            Player.historyId = data.historyId;
            Player.lag = 0;
            Player.audio.src = "/api/v1/songs/" + encodeURIComponent(data.id) + "/stream" +
                (position > 0 ? "#t=" + position.toFixed(1) : "");
            Player.audio.play().catch((error) => {
                // the browser wants a click first, a new song interrupting is fine
                if (error.name === "NotAllowedError") {
                    Player.stop();
                }
            });

            if ("mediaSession" in navigator && typeof window.MediaMetadata === "function") {
                navigator.mediaSession.metadata = new window.MediaMetadata({
                    title: data.title,
                    artist: data.artist.name || "",
                    album: data.album.title || ""
                });
            }
        },

        setButton: function () {
            const label = Player.listening ? gettext("Stop listening") : gettext("Listen");
            $("#listen")
                .toggleClass("playing", Player.listening)
                .attr({"aria-pressed": String(Player.listening), "title": label, "aria-label": label});
            $("#nowPlaying").toggleClass("listening", Player.listening);
        }
    };

    // a stable color per artist for the cover placeholder
    function hue(text) {
        let hash = 0;
        for (let i = 0; i < text.length; i++) {
            hash = (hash * 31 + text.charCodeAt(i)) % 360;
        }
        return hash;
    }

    const Music = {
        url: null,
        pageNum: 1,
        hasNextPage: false,
        loading: false,
        generation: 0,
        options: {},
        searchOptions: {},
        // server clock of the current song, advanced every second
        position: 0,
        length: 0,
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

            Player.init();
            Music.getCurrentSong();
            Music.ping();
            Music.setActiveMenu($("#sidebar a.loadQueue"));
            Music.loadList("/api/v1/queue");
        },

        showSongs: function (options) {
            Music.options = options;
            Music.setActiveMenu($("#sidebar a.loadSongs"));
            Music.loadList("/api/v1/songs");
        },

        initSearch: function () {
            $("#searchform").on("submit", () => {
                Music.showSongs({"search_term": $("input.searchterm").val()});
                return false;
            });

            $("#searchdetailsform").on("submit", () => {
                Music.showSongs(Music.getSearchOptions());
                Music.toggleSearchDetails(false);
                return false;
            });
            $("#searchdetailsform .searchreset").on("click", () => {
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
            $("#search_title").trigger("focus");
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

            $(document).on("keydown", (event) => {
                if (event.key === "Escape") {
                    Music.toggleSearchDetails(false);
                    $(document).off("click.account");
                    $("#accountoptions").hide();
                }
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

            main.on("click", "table.list button.vote:not(.active)", function () {
                $.ajax({
                    url: "/api/v1/queue",
                    type: "POST",
                    data: {"id": $(this).attr("data-id")}
                }).done((data) => {
                    const items = $("button.vote[data-id=\"" + data.id + "\"]");
                    setToggle(items, true, gettext("Revoke vote"));
                    items.closest("tr").find(".voteCount .count").text(data.count);
                });
                return false;
            });

            main.on("click", "table.list button.vote.active", function () {
                const inQueue = $(this).closest("tr.row_queue").length > 0;
                $.ajax({
                    url: "/api/v1/queue/" + encodeURIComponent($(this).attr("data-id")),
                    type: "DELETE"
                }).done((data) => {
                    const items = $("button.vote[data-id=\"" + data.id + "\"]");
                    if (inQueue && data.count === 0) {
                        items.closest("tr").fadeOut(400, function () {
                            $(this).remove();
                        });
                        return;
                    }
                    setToggle(items, false,
                        inQueue ? gettext("Support vote") : gettext("Vote to play"));
                    items.closest("tr").find(".voteCount .count").text(data.count);
                });
                return false;
            });

            main.on("click", "table.list button.favourite:not(.active)", function () {
                $.ajax({
                    url: "/api/v1/favourites",
                    type: "POST",
                    data: {"id": $(this).attr("data-id")}
                }).done((data) => {
                    setToggle($("button.favourite[data-id=\"" + data.id + "\"]"), true,
                        gettext("Remove from favourites"));
                });
                return false;
            });

            main.on("click", "table.list button.favourite.active", function () {
                const inFavourites = $(this).closest("tr.row_favourites").length > 0;
                $.ajax({
                    url: "/api/v1/favourites/" + encodeURIComponent($(this).attr("data-id")),
                    type: "DELETE"
                }).done((data) => {
                    const items = $("button.favourite[data-id=\"" + data.id + "\"]");
                    if (inFavourites) {
                        items.closest("tr").fadeOut(400, function () {
                            $(this).remove();
                        });
                        return;
                    }
                    setToggle(items, false, gettext("Add to favourites"));
                });
                return false;
            });

            main.on("mouseenter", "td.voteCount", function () {
                const rect = this.getBoundingClientRect();
                $(this).find("div.voteTooltip").css({
                    left: rect.left,
                    top: rect.bottom + 4
                }).show();
            });
            main.on("mouseleave", "td.voteCount", function () {
                $(this).find("div.voteTooltip").hide();
            });
        },

        ping: function () {
            $.ajax({url: "/api/v1/ping"}).always(() => {
                setTimeout(Music.ping, PING_INTERVAL);
            });
        },

        getCurrentSong: function () {
            clearTimeout(Music.currentSongTimer);
            $.ajax({url: "/api/v1/songs/current"}).done((data) => {
                Player.receive(data);
                Music.showCurrentSong(data);
                if ("id" in data) {
                    Music.position = data.position;
                    Music.length = data.length;
                    Music.tick();
                }
                else {
                    Music.currentSongTimer = setTimeout(Music.getCurrentSong, 10000);
                }
            }).fail(() => {
                Music.currentSongTimer = setTimeout(Music.getCurrentSong, 10000);
            });
        },

        showCurrentSong: function (data) {
            const bar = $("#nowPlaying");
            const playing = "id" in data;
            bar.toggleClass("idle", !playing);
            if (!playing) {
                bar.find(".songTitle").text(gettext("Nothing is playing yet"));
                bar.find(".songArtist, .npVotes, .cover span").text("");
                bar.find(".elapsed, .duration").text(formatLength(0));
                bar.find(".fill").css("width", 0);
                return;
            }

            const artist = data.artist.name || "";
            bar.find(".songTitle").text(data.title).attr("title", data.title);
            bar.find(".songArtist").text(data.album.title ? artist + " · " + data.album.title : artist);
            bar.find(".cover").css("--hue", hue(artist)).find("span").text(artist.charAt(0).toUpperCase());
            bar.find(".npVotes").html(votePill(data))
                .attr("title", data.users.map((user) => user.name).join(", "));
        },

        // advance the progress with the server clock, ask for the next song once it's over
        tick: function () {
            const remaining = Music.length - Music.position;
            if (remaining <= 0) {
                // poll quickly until the next song is picked
                Music.currentSongTimer = setTimeout(
                    Music.getCurrentSong, remaining > -30 ? 2000 : 10000);
                return;
            }

            const progress = Math.min(Music.position / Music.length * 100, 100) + "%";
            $("#nowPlaying .fill").css("width", progress);
            $("#nowPlaying .elapsed").text(formatLength(Music.position));
            $("#nowPlaying .duration").text(formatLength(Music.length));
            Music.position++;
            Music.currentSongTimer = setTimeout(Music.tick, 1000);
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

        renderHeader: function (terms) {
            const title = $("#sidebar li.active .label").text();
            let html = "<div class=\"listHeader\"><h1>" + escapeHtml(title) + "</h1>";
            if (terms) {
                html += "<span class=\"searchSummary\">" + escapeHtml(terms) + "</span>";
            }
            return html + "</div>";
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

                Music.hasNextPage = data.hasNextPage;
                let html = Music.renderHeader(terms.join(" "));
                if (data.itemList.length > 0) {
                    html += Music.renderTable(data);
                }
                else {
                    html += "<div class=\"noContent\">" + ICONS.empty +
                        escapeHtml(gettext("No data found")) + "</div>";
                }
                $("#main").html(html);
                $("#main table.list tbody").append(Music.renderData(data));
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

        hideAttribute: function (col) {
            return col.hide ? " data-hide=\"" + col.hide + "\"" : "";
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
                        Music.getOrderClass(col.sort, data) + "\" data-sort=\"" + col.sort + "\"" +
                        Music.hideAttribute(col) + ">";
                }
                else {
                    html += "<th class=\"" + col.cls + "\"" + Music.hideAttribute(col) + ">";
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
                    html += "<td class=\"actions\">";
                    html += item.queued
                        ? toggleButton("vote", item.id, true, gettext("Revoke vote"))
                        : toggleButton("vote", item.id, false, list.voteLabel);
                    html += item.favourite || list.alwaysFavourite
                        ? toggleButton("favourite", item.id, true, gettext("Remove from favourites"))
                        : toggleButton("favourite", item.id, false, gettext("Add to favourites"));
                    html += "</td>";
                }
                list.columns.forEach((col) => {
                    // cells start with "<td", mark the ones small screens leave out
                    html += col.cell(item).replace(/^<td/, "<td" + Music.hideAttribute(col));
                });
                html += "</tr>";
            });
            return html;
        }
    };

    window.Music = Music;
    $(Music.init);
}(jQuery));
