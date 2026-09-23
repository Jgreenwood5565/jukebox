import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a local jukebox account, or set a new password for an existing one"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--name", default="", help="Display name, e.g. 'Jane Doe'")
        parser.add_argument(
            "--admin", action="store_true", help="Allow access to the admin interface"
        )

    def handle(self, *args, **options):
        User = get_user_model()  # noqa: N806
        username = options["username"].strip()
        if not username:
            raise CommandError("Username must not be empty")

        user = User.objects.filter(username=username).first()
        created = user is None
        if created:
            user = User(username=username)
        if options["name"]:
            first, _, last = options["name"].strip().partition(" ")
            user.first_name, user.last_name = first, last
        if options["admin"]:
            user.is_staff = user.is_superuser = True

        password = self.read_password(user)
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created user {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated user {username}"))

    def read_password(self, user):
        while True:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                self.stderr.write("Passwords don't match")
                continue
            try:
                validate_password(password, user)
            except ValidationError as e:
                self.stderr.write("\n".join(e.messages))
                continue
            return password
