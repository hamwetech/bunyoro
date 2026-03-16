from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from conf.utils import generate_numeric
from coop.models import CooperativeMember

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        member = CooperativeMember.objects.all()
        count = 1
        for m in member:
            today = datetime.today()
            datem = today.year
            yr = str(datem)[2:]
            # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
            fint = "%04d"%count
            idno = str(m.cooperative.code)+yr+fint
            m.member_id = idno
            m.save()
            print "Cooperative %s code is %s" % (m.cooperative.code, idno)
            count += 1