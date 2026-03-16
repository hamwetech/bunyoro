import os
import time
from django.core.management.base import BaseCommand
from django.db.models import Q, CharField, Max, Sum, Count, Value as V
from coop.models import CooperativeMember
from api.TIV import DataSender

LOCK_FILE_PATH = '/tmp/my_management_command.lock'

class Command(BaseCommand):
    help = 'Get information from CooperativeMember model'

    def handle(self, *args, **options):
        # Check if the lock file exists
        if os.path.exists(LOCK_FILE_PATH):
            self.stdout.write(self.style.ERROR("Command is already running. Exiting."))
            return
        # Create the lock file
        with open(LOCK_FILE_PATH, 'w') as lock_file:
            lock_file.write(str(os.getpid()))

        try:
            members = CooperativeMember.objects.exclude(Q(consumer_device_id="")|Q(consumer_device_id="null"))
            # time.sleep(10)
            for member in members:
                if not member.sent_to_tiv:
                    data_sender = DataSender()
                    data_sender.register(member)
                    time.sleep(1)
            self.stdout.write(self.style.SUCCESS("Command completed successfully."))
        finally:
            # Remove the lock file when the command finishes
            os.remove(LOCK_FILE_PATH)