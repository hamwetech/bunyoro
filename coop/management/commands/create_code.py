from django.core.management.base import BaseCommand, CommandError
from conf.utils import get_consontant_upper
from coop.models import Cooperative

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        coop = Cooperative.objects.all()
        count = 1
        for m in coop:
            name = m.name
            if name:
                code = get_consontant_upper(name)
                try:
                    m.code = code
                    m.save()
                except Exception:
                    code = name.upper()[:3]
                    m.code = code
                    m.save()
                print "Cooperative %s code is %s" % (name, code)
                count =+ count