# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    reference = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creator = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    transaction_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account"

    def __unicode__(self):
        return "%s" % self.reference


class AccountTransaction(models.Model):
    account = models.ForeignKey(Account)
    reference = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=32, decimal_places=2)
    balance_after = models.DecimalField(max_digits=32, decimal_places=2, null=True, blank=True)
    transaction_type = models.CharField(max_length=64, choices=(('COLLECTION', 'COLLECTION'), ('AIRTIME', 'AIRTIME'),
                                                                ('PAYOUT', 'PAYOUT')))
    entry_type = models.CharField(max_length=15, choices=(('CREDIT', 'CREDIT'), ('DEBIT', 'DEBIT')))
    category = models.CharField(max_length=15, choices=(('REGISTRATION', 'REGISTRATION'),))
    status =  models.CharField(max_length=15, choices=(('PENDING', 'PENDING'), ('SUCCESSFUL', 'SUCCESSFUL'), ('FAILED', 'FAILED'), ('INDETERMINATE', 'INDETERMINATE'),('CANCELED', 'CANCELED'),))
    description = models.CharField(max_length=255)
    request = models.TextField()
    request_date = models.DateField()
    response = models.TextField(null=True, blank=True)
    response_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_transaction"

    def __unicode__(self):
        return "%s" % self.transaction_reference


