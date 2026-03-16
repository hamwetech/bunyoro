# your_app/management/commands/insert_loan_transactions.py

from django.core.management.base import BaseCommand
from credit.models import LoanRequest, LoanTransaction

class Command(BaseCommand):
    help = 'Inserts records into LoanTransaction for approved LoanRequests'

    def handle(self, *args, **kwargs):
        approved_requests = LoanRequest.objects.filter(status='APPROVED')

        for request in approved_requests:
            # Create LoanTransaction record
            transaction = LoanTransaction.objects.create(
                reference=request.reference,  # Adjust as per your model fields
                member=request.member,
                credit_manager=request.credit_manager,
                amount=request.requested_amount,
                transaction_type='CREDIT',  # Adjust as per your requirement
                loan=request,
                # Add other fields as required
            )

            self.stdout.write(self.style.SUCCESS("Successfully created transaction for LoanRequest: %s " % request.reference))
