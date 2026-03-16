import datetime
from payment.utils import payment_transction
from coop.AccountTransactions import AccountTransaction
from payment.models import MemberPayment, MemberPaymentTransaction, MobileMoneyRequest

from conf.utils import generate_alpanumeric, log_debug, log_error


class PaymentTransaction:
    member = None
    request = None
    
    def __init__(self, member, request):
        self.member = member
        self.request = request
        
    def transaction_request(self, params=None, payment_request=None):
        
        try:
            if not payment_request:
                cooperative = params.get('cooperative')
                amount = params.get('amount')
                payment_date = params.get('payment_date')
                payment_method = params.get('payment_method')
                user = params.get('user')
                status = params.get('status')
                
                payment_request = MemberPaymentTransaction.objects.create(
                    transaction_reference = generate_alpanumeric('60', 10),
                    cooperative = cooperative,
                    member = self.member,
                    amount = amount,
                    payment_date = payment_date,
                    payment_method = payment_method,
                    creator = user,
                    status = status
                )
            if payment_request.payment_method != "MOBILE MONEY":
                payment_request.status = 'SUCCESSFUL'
            if payment_request.payment_method == "MOBILE MONEY":
                res = self.mobile_money_transation(payment_request)
                payment_request.status = res['status']
                payment_request.save()
            if payment_request.status == 'SUCCESSFUL':
                bal_before = payment_request.member.paid_amount
                bal_after = payment_request.amount + bal_before
                
                payment_request.balance_before = bal_before
                payment_request.balance_after = bal_after
                payment_request.save()
                
                # update user account
                at = AccountTransaction(self.member)
                at._update_payment(bal_after)
        except Exception as e:
            log_error()
            
    def mobile_money_transation(self, payment_request):
        try:
            transaction_reference = generate_alpanumeric('WC', 12)
            phone_number = payment_request.member.phone_number
            member = self.member
            msisdn = self.member.phone_number
            amount = payment_request.amount
            status = 'PENDING'
            request = ''
            user = self.request.user
            
            mm_request = MobileMoneyRequest.objects.create(
                transaction_reference = transaction_reference,
                phone_number = phone_number,
                member = member,
                amount = amount,
                status = status,
                request = request,
                user = user,
            )
            
            reference = mm_request.transaction_reference
            res = payment_transction(msisdn, amount, reference)
            status = res['status']
            if res['status'] == 'ERROR':
                status = 'FAILED'
            if res['status'] == 'OK':
                status = res['transactionStatus']
            mm_request.status = status
            mm_request.response = res
            mm_request.response_date = datetime.datetime.now()
            mm_request.save()
            return {"status": mm_request.status}
        except Exception as e:
            log_error()
            return {"status": "FAILED"}
            
    def save_transation(self, request, payment_request):
        try:
           pass
        except Exception as e:
            log_error()
        