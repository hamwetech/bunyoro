# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from coop.models import CooperativeMember


class Partner(models.Model):
    name = models.CharField(max_length=64, unique=True)
    code = models.CharField(max_length=64, null=True, blank=True)
    logo = models.ImageField(upload_to='partner/', null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=0)
    address = models.TextField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partner'#code
        
    def __unicode__(self):
        return self.name
        
        
class PartnerStaff(models.Model):
    title = (
        ('Mr', 'Mr'),
        ('Miss', 'Miss'),
        ('Mrs', 'Mrs'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
        ('Hon', 'Hon'),
        )
    partner = models.ForeignKey(Partner)
    photo = models.ImageField(upload_to='partner/staff/', null=True, blank=True)
    title = models.CharField(max_length=25, choices=title, null=True, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    other_name = models.CharField(max_length=150, null=True, blank=True)
    role = models.CharField(max_length=150, choices=(('Excecutive','Excecutive'), ('Business Development','Business Development'), ('Sales Representative', 'Sales Representative')))
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=0)
    user = models.OneToOneField(User, related_name='system_user', null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partner_staff'
        
    
    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)
    
    
    
    

