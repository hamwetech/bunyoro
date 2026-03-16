from django.core.management.base import BaseCommand, CommandError
from conf.utils import get_consontant_upper, generate_numeric
from coop.models import Cooperative, CooperativeMember
from account.models import Account


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        coop = Cooperative.objects.all()
        for m in coop:
            if not m.account:
                account = Account.objects.create(reference=generate_numeric(size=8))
                m.account = account
                m.save()
                print("Cooperative Account created %s " % account)

        members = CooperativeMember.objects.all()
        for member in members:
            if not member.account:
                account = Account.objects.create(reference=generate_numeric(size=8))
                member.account = account
                member.save()
                print("Member Account created %s " % account)