from django.contrib.syndication.views import Feed
from django.db.models import Count
from django.urls import reverse

from .models import Queue


class QueueFeed(Feed):
    title = "Jukebox Queue Feed"
    description = "Top song in the queue"

    def link(self):
        return reverse("jukebox_web_index")

    def items(self):
        # same order the player uses to pick the next song
        return (
            Queue.objects.select_related("Song__Artist", "Song__Album")
            .annotate(VoteCount=Count("User"))
            .order_by("-VoteCount", "Created")[:1]
        )

    def item_title(self, item):
        return item.Song.Title

    def item_description(self, item):
        description = f"{item.Song.Title} by {item.Song.Artist}"
        if item.Song.Album is not None:
            description += f" from {item.Song.Album}"
        return description

    def item_link(self, item):
        # songs have no page of their own, make the link unique per queue entry
        return f"{reverse('jukebox_web_index')}#queue-{item.pk}"

    def item_pubdate(self, item):
        return item.Created
