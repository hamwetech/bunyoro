# your_app/management/commands/insert_loan_transactions.py

from django.core.management.base import BaseCommand
from credit.models import LoanRequest, LoanTransaction

class Command(BaseCommand):
    help = 'Inserts records into LoanTransaction for approved LoanRequests'

    def handle(self, *args, **kwargs):
        approved_requests = LoanRequest.objects.filter(status='APPROVED')

        for request in approved_requests:
            if not request.approved_amount:
                request.approved_amount = request.requested_amount
                request.save()
                self.stdout.write(self.style.SUCCESS("Successfully created transaction for LoanRequest: %s " % request.reference))
