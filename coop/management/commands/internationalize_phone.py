from django.core.management.base import BaseCommand, CommandError
from conf.utils import internationalize_number
from coop.models import CooperativeMember

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        member = CooperativeMember.objects.all()
        for m in member:
            phone_number = m.phone_number
            if phone_number:
                try:
                    new_phone_number = internationalize_number(phone_number)
                    print "Internationalized %s to %s " % (phone_number, new_phone_number)
                    m.phone_number = new_phone_number
                    m.save()
                except Exception as e:
                    print "ERROR: %s is an invalid number " % phone_number 
        