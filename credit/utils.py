import datetime
from credit.models import LoanTransaction, LoanRequest
from conf.utils import generate_alpanumeric, generate_numeric


def create_loan_transaction(params):
    member = params.get('member')
    loan = params.get('loan')
    credit_manager = params.get('credit_manager')
    amount = params.get('amount')
    transaction_type = params.get('transaction_type')
    created_by = params.get('created_by')

    reference = generate_numeric(8, "45")

    LoanTransaction.objects.create(
        reference=reference,
        loan=loan,
        member=member,
        credit_manager=credit_manager,
        amount=amount,
        transaction_type=transaction_type,
        created_by=created_by
    )

    # if transaction_type == "DEBIT":
    #     amount = -amount
    return amount


def check_loan(member):
    try:
        loanr = LoanRequest.objects.filter(member=member)
        if loanr.exists():
            return loanr
        return None
    except Exception:
        return None


def pay_loan(params):
    member = params.get('member')
    amount = params.get('amount')

    loanr = LoanRequest.objects.filter(member=member)
    if loanr.exists():
        for loan in loanr:
            balance = loan.requested_amaount - loan.paid_amount
            if balance > 0:
                if balance > amount:
                    pay = amount
                if balance <= amount:
                    pay = balance
                    loan.status = 'PAID'

                loan.paid_amount = pay
                loan.last_payment_date = datetime.datetime.now()
                loan.save()
                ploan = {
                    "member": member,
                    "loan": loan,
                    "credit_manager": loan.credit_manager,
                    "amount": amount,
                    "transaction_type": "LOAN REPAYMENT",
                    "created_by": "SYSTEM"
                }
                amount = amount - pay
                create_loan_transaction(ploan)
