# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from conf.models import District, PaymentMethod
from partner.models import Partner, PartnerStaff
from coop.models import Cooperative, CooperativeMember
from product.models import Product, ProductVariation


class Purchase(models.Model):
    purchaser = models.CharField(max_length=10, blank=True, choices=(('PARTNER', 'PARTNER'), ('COOP', 'COOP'),
        ('UNDEFINED', 'UNDEFINED')), default='UNDEFINED')
    transaction_id = models.CharField(max_length=150, null=True, blank=True)
    bill_of_sale = models.CharField(max_length=124, null=True, blank=True)
    seller_name = models.CharField(max_length=254)
    seller_msisdn = models.CharField(max_length=25)
    farm_name = models.CharField(max_length=124, null=True, blank=True)
    address = models.CharField(max_length=124, null=True, blank=True)
    town = models.CharField(max_length=124, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    gps_coodinates = models.CharField(max_length=124, null=True, blank=True)
    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, blank=True)
    farmer_verification = models.BooleanField(default=0)
    witness_name = models.CharField(max_length=125, null=True, blank=True)
    witness_msisdn = models.CharField(max_length=25, null=True, blank=True)
    witness_verification = models.BooleanField(default=0)
    transaction_date = models.DateTimeField()
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase'
        
    def __unicode__(self):
        return self.transaction_id
    

class PurchaseVerification(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    seller_code = models.CharField(max_length=10)
    sc_attemps = models.PositiveIntegerField()
    sc_used = models.BooleanField(default=0)
    sc_entry_date = models.DateTimeField(null=True, blank=True)
    withness_code = models.CharField(max_length=10)
    witness_code = models.CharField(max_length=10)
    wc_attemps = models.PositiveIntegerField()
    wc_used = models.BooleanField(default=0)
    wc_entry_date = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)                                 
    
    class Meta:
        db_table = 'purchase_verification'
    
    def __unicode__(self):
        return self.seller_code
    

class PurchaseProduct(models.Model):
    purchase = models.ForeignKey(Purchase, blank=True, on_delete=models.CASCADE)
    breed = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    count = models.PositiveIntegerField()
    identification = models.CharField(max_length=124, null=True, blank=True)
    coat_color = models.CharField(max_length=124, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    quantity = models.DecimalField('Weight', max_digits=20, decimal_places=2)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)                                 
    
    class Meta:
        db_table = 'purchase_product'
    
    def __unicode__(self):
        return self.identification


class PartnerPurchaseTransaction(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    partner_staff = models.ForeignKey(PartnerStaff, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partner_purchase_transaction'
    
    def __unicode__(self):
        return self.partner
        

class PurchasePaymentLog(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=254)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    transaction_type = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    indicator = models.TextField(null=True, blank=True)
    indicator_file = models.FileField(upload_to='purchase/document/', null=True, blank=True)
    transaction_date = models.DateTimeField()
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_payment_log'
        
    def __unicode__(self):
        return self.transaction_id
    
class MemberPurchaseTransaction(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'member_purchase_transaction'
        
    def __unicode__(self):
        return "%s" % self.member
    
    
    