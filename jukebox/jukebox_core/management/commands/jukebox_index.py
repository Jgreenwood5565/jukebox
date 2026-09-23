import os

from django.core.management.base import BaseCommand, CommandError

# FileIndexer is imported from here by the jukebox_live_indexer plugin
from jukebox.jukebox_core.utils import FileIndexer


class Command(BaseCommand):
    help = "Add all music files below a directory to the jukebox library"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Music library path to scan")

    def handle(self, *args, **options):
        path = os.path.abspath(options["path"])
        if not os.path.isdir(path):
            raise CommandError(f"Path does not exist: {path}")

        self.stdout.write(f"Indexing music in {path}")
        self.stdout.write("This may take a while")

        indexer = FileIndexer()
        verbosity = options["verbosity"]
        added = 0
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for name in sorted(files):
                filename = os.path.join(root, name)
                if verbosity >= 2:
                    self.stdout.write(f"Indexing file {filename}")
                if indexer.index(filename) is not None:
                    added += 1

        self.stdout.write(self.style.SUCCESS(f"Added {added} songs"))
