class AccountTransaction():
    
    def __init__(self, member):
        self.member = member
        
    def _update_payment(self, amount):
        self.member.paid_amount = amount
        self.member.save()