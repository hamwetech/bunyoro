from django.core.management.base import BaseCommand
from coop.models import Cooperative, CooperativeMember
import re

class Command(BaseCommand):
    args = '<file_path>'
    help = 'Read text from a file and extract id_number and card_number values'


    def handle(self, *args, **options):
        # if not args:
        #     self.stderr.write('Usage: python manage.py read_log <file_path>')
        #     return

        file_path = '/home/centos/mastercard_raw/id.txt'

        with open(file_path, 'r') as file:
            for line in file:
                id_number_match = re.search(r"id_number: (.*?),", line)
                card_number_match = re.search(r"card_number: (.*?)$", line)
                id_number = id_number_match.group(1) if id_number_match else None
                card_number = card_number_match.group(1) if card_number_match else None
                if id_number and card_number:
                    try:
                        coop = CooperativeMember.objects.filter(card_number=card_number)
                        if coop.exists():
                            mber = coop[0]
                            mber.id_number = id_number
                            mber.save()
                            self.stdout.write('id_number: {}, card_number: {}'.format(id_number, card_number))
                    except Exception as e:
                        self.stdout.write('{}'.format(e))
