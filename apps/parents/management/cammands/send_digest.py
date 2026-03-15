"""
Management command to send daily digest emails
Run: python manage.py send_digest
"""

from django.core.management.base import BaseCommand
from apps.parents.tasks import process_daily_digest


class Command(BaseCommand):
    help = 'Send daily digest emails to parents'

    def handle(self, *args, **options):
        self.stdout.write("Sending daily digest emails...")
        count = process_daily_digest()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} digest emails"))