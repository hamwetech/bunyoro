# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from coop.models import CooperativeMember, MemberOrder, OrderItem
from django.contrib.auth.models import User


class CreditManager(models.Model):
    name = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=120)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    contact_phone_number = models.CharField(max_length=255, null=True, blank=True)
    api_username = models.CharField(max_length=255, null=True, blank=True)
    api_password = models.CharField(max_length=255, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credit_manager'

    def __unicode__(self):
        return "%s" % self.name


class CreditManagerAdmin(models.Model):
    user = models.OneToOneField(User, blank=True, related_name='cm_admin')
    credit_manager = models.ForeignKey(CreditManager, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s" % self.user.get_full_name()


class LoanRequest(models.Model):
    reference = models.CharField(max_length=255, unique=True)
    member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    credit_manager = models.ForeignKey(CreditManager, null=True, blank=True)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    request_date = models.DateTimeField()
    order_item = models.ForeignKey(OrderItem, null=True, blank=True, on_delete=models.SET_NULL)
    deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=64, choices=(('PENDING', 'PENDING'), ('PROCESSING', 'PROCESSING'),
                                                      ('ACCEPTED', 'ACCEPTED'), ('REJECTED', 'REJECTED'),
                                                      ('INPROGRESS', 'INPROGRESS'), ('PAID', 'PAID'), ('APPROVED', 'APPROVED')), default='PENDING')
    confirm_date = models.DateTimeField(null=True, blank=True)
    loan_reference = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    reject_reason = models.TextField(null=True, blank=True)
    loan_request_id = models.CharField(max_length=255, null=True, blank=True)
    agent = models.CharField(max_length=255, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_request'

    def __unicode__(self):
        return "%s - %s | %s/-" % (self.member.get_name(), self.reference, self.approved_amount) or u''


class LoanTransaction(models.Model):
    reference = models.CharField(max_length=255, unique=True)
    member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    credit_manager = models.ForeignKey(CreditManager, null=True, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=16, choices=(('CREDIT', 'CREDIT'), ('DEBIT', 'DEBIT')))
    loan = models.ForeignKey(LoanRequest, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_transaction'

    def __unicode__(self):
        return "%s" % self.member.get_name() or u''

class LoanRepaymentTransaction(models.Model):
    request = models.ForeignKey(LoanRequest, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=9, decimal_places=2)
    balance = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    repayment_date = models.DateTimeField()
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_repayment'

    def __unicode__(self):
        return "%s" % self.request.member.get_name() or u''