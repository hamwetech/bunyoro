from django.core.management.base import BaseCommand
from conf.utils import send_email_with_logo
from django.template.loader import render_to_string

class Command(BaseCommand):
    help = 'A brief description of your command'

    def handle(self, *args, **options):
        send_email_with_logo("HEllo bwana", "geoffrey.w.ndungu@gmail.com")
        self.stdout.write(self.style.SUCCESS('This is a sample Django management command!'))