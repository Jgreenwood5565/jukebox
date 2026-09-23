from django.conf import settings
from django.db import models


class Artist(models.Model):
    Name = models.CharField(max_length=200)

    class Meta:
        ordering = ["Name"]

    def __str__(self):
        return self.Name


class Genre(models.Model):
    Name = models.CharField(max_length=200)

    class Meta:
        ordering = ["Name"]

    def __str__(self):
        return self.Name


class Album(models.Model):
    Title = models.CharField(max_length=200)

    class Meta:
        ordering = ["Title"]

    def __str__(self):
        return self.Title


class Song(models.Model):
    Artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    Album = models.ForeignKey(Album, null=True, blank=True, on_delete=models.SET_NULL)
    Genre = models.ForeignKey(Genre, null=True, blank=True, on_delete=models.SET_NULL)
    Title = models.CharField(max_length=200)
    Year = models.IntegerField(null=True, blank=True)
    Length = models.IntegerField()
    Filename = models.CharField(max_length=1000)

    class Meta:
        ordering = ["Title", "Artist", "Album"]

    def __str__(self):
        return f"{self.Artist.Name} - {self.Title}"


class Queue(models.Model):
    Song = models.OneToOneField(Song, on_delete=models.CASCADE)
    User = models.ManyToManyField(settings.AUTH_USER_MODEL)
    Created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.Song)


class Favourite(models.Model):
    Song = models.ForeignKey(Song, on_delete=models.CASCADE)
    User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    Created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("Song", "User")]
        ordering = ["-Created"]

    def __str__(self):
        return str(self.Song)


class History(models.Model):
    Song = models.ForeignKey(Song, on_delete=models.CASCADE)
    User = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    Created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-Created"]
        verbose_name_plural = "history"

    def __str__(self):
        return str(self.Song)


class Player(models.Model):
    Pid = models.IntegerField()

    def __str__(self):
        return str(self.Pid)
