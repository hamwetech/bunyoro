from messaging.utils import sendSMS
from conf.utils import log_debug, log_error
from coop.models import Cooperative

def sendMemberSMS(request, member, message):
    if member.cooperative:
        if member.cooperative.send_message:
            msisdn = member.phone_number
            try:
                log_debug('Message: %s Receiver: %s' % (message, msisdn))
                sendSMS(request, msisdn, message)

                return True
            except Exception:
                log_error()
                return False
    return False


def check_coop_url(str):
    coop = Cooperative.objects.filter(system_url__icontains=str)
    if coop.exists():
        coop = coop[0]
    return coop



def credit_member_account(params):
    member = params.get('member')
    amount = params.get("amount")
    transaction_category = params.get("transaction_category")
    balance_before = member.account.balance if member.account else 0
    new_balance = balance_before + amount
    params.update({"new_balance": new_balance})
    member.account.balance = new_balance
    member.account.save()

    create_transaction(params)


def debit_member_account(params):
    member = params.get('member')
    amount = params.get("amount")
    balance_before = member.account.balance if member.account else 0
    new_balance = balance_before - amount
    params.update({"new_balance": new_balance})
    member.account.balance = new_balance
    member.account.save()
    create_transaction(params)
