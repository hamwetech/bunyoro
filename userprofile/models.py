# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pyotp
from django.db import models
from django.dispatch import receiver
from datetime import datetime, date
from django.contrib.auth.models import User, AbstractUser
from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from conf.models import *


class AccessLevel(models.Model):
    name = models.CharField(max_length=15, unique=True)
    create_date = models.DateTimeField(auto_now=True)
    update_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'access_level'
    
    def __unicode__(self):
        return self.name
    

class AccessLevelGroup(models.Model):
    access_level = models.OneToOneField(AccessLevel, unique=True, related_name='group_links')
    group = models.ManyToManyField(Group, related_name='access_levels')
    
    class Meta:
        db_table = 'access_levell_group'
    
    def __unicode__(self):
        return "%s" % self.access_level


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    profile_photo = models.ImageField(upload_to='user/', null=True)
    sex = models.CharField('Sex', max_length=10, choices=(('Male', 'Male'), ('Female', 'Female')), null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    msisdn = models.CharField(max_length=12, unique=True, null=True, blank=True)
    nin = models.CharField(max_length=255,  null=True, blank=True)
    access_level = models.ForeignKey(AccessLevel, null=True, blank=True, on_delete=models.CASCADE)
    district = models.ForeignKey(District, null=True, blank=True, on_delete=models.SET_NULL, related_name="profile_district")
    county = models.ForeignKey(County, null=True, blank=True, on_delete=models.SET_NULL)
    sub_county = models.ForeignKey(SubCounty, null=True, blank=True, on_delete=models.SET_NULL)
    parish = models.ForeignKey(Parish, null=True, blank=True, on_delete=models.SET_NULL)
    village = models.CharField(max_length=150, null=True, blank=True)
    gps_coodinates = models.CharField(max_length=150, null=True, blank=True)
    district_incharge = models.ManyToManyField(District, null=True, blank=True)
    is_supervisor = models.BooleanField(default=False)
    supervisor = models.ForeignKey(User, null=True, blank=True, related_name="supervisor")
    is_locked = models.BooleanField(default=0)
    receive_sms_notifications = models.BooleanField(default=0)
    create_date = models.DateTimeField(auto_now=True)
    update_date = models.DateTimeField(auto_now_add=True)
    enable_mfa = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, blank=True, null=True)


    # === 🔐 TOTP METHODS ===
    def get_otp_secret(self):
        """Generate or return the user's TOTP secret key."""
        if not self.otp_secret:
            self.otp_secret = pyotp.random_base32()
            self.save(update_fields=["otp_secret"])
        return self.otp_secret

    def get_totp(self):
        """Return the TOTP object using the user's secret key."""
        return pyotp.TOTP(self.get_otp_secret())

    def get_qr_uri(self):
        """
        Generate a provisioning URI for QR code apps like Google Authenticator.
        You can display this as a QR code for first-time setup.
        """
        return self.get_totp().provisioning_uri(
            name=self.user.email or self.user.username,
            issuer_name="YourAppName"
        )

    def verify_totp(self, code):
        """Verify a 6-digit OTP code entered by the user."""
        return self.get_totp().verify(code)
 
    class Meta:
        db_table = 'user_profile'

    @property
    def age(self):
        if self.date_of_birth:
            m = date.today() - self.date_of_birth
            return m.days / 365
        return None
        
    def is_union(self):
        if self.access_level:
            if self.access_level.name.upper() == "UNION" or self.access_level.name.upper() == "TERRITORY":
                return True
        if self.user.is_superuser:
            return True
        return False
    
    def is_cooperative(self):
        if self.access_level:
            if self.access_level.name.upper() == "COOPERATIVE":
                return True
        if self.user.is_superuser:
            return True
        return False
    
    def is_partner(self):
        if self.access_level:
            if self.access_level.name.upper() == "PARTNER":
                return True
        if self.user.is_superuser:
            return True
        return False
    
    def is_union_admin(self):
        if self.access_level.name.upper() == "UNION" or self.user.is_superuser:
            return True
        return False

    def get_cards(self):
        cards = AssignedCards.objects.filter(assigned_to=self.user)
        number = 0
        if cards.exists():
            card = cards[0]
            number = card.number_of_cards
        return number

    def has_device(self):
        devices = Device.objects.filter(assigned_to=self.user)
        if devices.exists():
            return True
        return False

    def get_te_device(self):
        devices = Device.objects.filter(in_charge=self.user)
        if devices.exists():
            return devices.count()
        return 0

    def has_gps(self):
        if self.gps_coodinates:
            return True
        return False

    def __str__(self):
        return self.user.get_full_name()
        

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Token.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Device(models.Model):
    device_id = models.CharField(max_length=255, unique=True)
    in_charge = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE, related_name="person_incharge")
    assigned_to = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device"

    def save(self, *args, **kwargs):
        self.device_id = self.device_id.upper()
        super(Device, self).save(*args, **kwargs)

    def __unicode__(self):
        return "%s" % self.device_id

class DeviceLocation(models.Model):
    longitude = models.CharField(max_length=255)
    latitude = models.CharField(max_length=255)
    location_date = models.CharField(max_length=255, null=True, blank=True)
    meta_data = models.TextField(null=True, blank=True)
    assigned_to = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=255,  null=True, blank=True)
    androidId = models.CharField(max_length=255,  null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_location"

    def __unicode__(self):
        return "%s" % self.longitude


class AssignedCards(models.Model):
    assigned_to = models.OneToOneField(User, on_delete=models.CASCADE)
    number_of_cards = models.PositiveIntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name="created_by")

    class Meta:
        db_table = "assigned_cards"

    def __unicode__(self):
        return "%s" % self.number_of_cards

