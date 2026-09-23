import json

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, transaction

LEGACY_SOCIAL_TABLE = "legacy_social_auth_usersocialauth"


class Command(BaseCommand):
    help = (
        "Upgrade a database created by jukebox < 0.5 (South, django-social-auth) "
        "to Django migrations, keeping the linked social accounts."
    )

    def handle(self, *args, **options):
        tables = set(connection.introspection.table_names())
        if "south_migrationhistory" not in tables:
            self.stdout.write("No legacy database found, running migrations")
            call_command("migrate", verbosity=options["verbosity"])
            return

        self.stdout.write("Preparing legacy database")
        with transaction.atomic(), connection.cursor() as cursor:
            quote = connection.ops.quote_name
            if "social_auth_usersocialauth" in tables and LEGACY_SOCIAL_TABLE not in tables:
                cursor.execute(
                    f"ALTER TABLE {quote('social_auth_usersocialauth')} "
                    f"RENAME TO {quote(LEGACY_SOCIAL_TABLE)}"
                )
            for table in ("social_auth_nonce", "social_auth_association"):
                if table in tables:
                    cursor.execute(f"DROP TABLE {quote(table)}")

        # tables that already exist are marked as migrated, the rest is migrated normally
        call_command("migrate", fake_initial=True, verbosity=options["verbosity"])

        if LEGACY_SOCIAL_TABLE in set(connection.introspection.table_names()):
            self.copy_social_accounts()

        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE {connection.ops.quote_name('south_migrationhistory')}")

        self.stdout.write(self.style.SUCCESS("Upgrade finished"))

    def copy_social_accounts(self):
        from social_django.models import UserSocialAuth

        quote = connection.ops.quote_name
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {quote('user_id')}, {quote('provider')}, {quote('uid')}, "
                    f"{quote('extra_data')} FROM {quote(LEGACY_SOCIAL_TABLE)}"
                )
                rows = cursor.fetchall()

            accounts = []
            for user_id, provider, uid, extra_data in rows:
                try:
                    extra_data = json.loads(extra_data) if extra_data else {}
                except ValueError:
                    extra_data = {}
                accounts.append(
                    UserSocialAuth(
                        user_id=user_id, provider=provider, uid=uid, extra_data=extra_data
                    )
                )
            UserSocialAuth.objects.bulk_create(accounts, ignore_conflicts=True)

            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE {quote(LEGACY_SOCIAL_TABLE)}")

        self.stdout.write(f"Kept {len(rows)} linked social accounts")
