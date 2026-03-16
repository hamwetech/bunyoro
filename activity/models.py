# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
from django.db import models
from django.contrib.auth.models import User
from coop.models import CooperativeMember, Cooperative
from product.models import ProductVariation

class ThematicArea(models.Model):
    thematic_area = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'thematic_area'
        
    def __unicode__(self):
        return self.thematic_area


class TrainingModule(models.Model):
    thematic_area = models.ForeignKey(ThematicArea, on_delete=models.CASCADE)
    topic = models.CharField(max_length=250)
    descriprion = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'training_module'
        
    def __unicode__(self):
        return "%s" % self.module


class TrainingAttendance(models.Model):
    training_module = models.ForeignKey(TrainingModule, null=True, blank=True, on_delete=models.CASCADE)
    training_reference = models.CharField(max_length=256, null=True, blank=True)
    trainer = models.ForeignKey(User, related_name='trainer', on_delete=models.CASCADE)
    coop_member = models.ManyToManyField(CooperativeMember, blank=True)
    gps_location = models.CharField(max_length=256, null=True, blank=True)
    training_start = models.DateTimeField()
    training_end = models.DateTimeField()
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'training_attendance'
        
    def __unicode__(self):
        return "%s" % self.coop_member
    
    def trainer_is_cooperative(self):
        if self.trainer.cooperative_admin:
            return True
        return False
    
class ExternalTrainer(models.Model):
    name = models.CharField(max_length=255)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "external_trainer"
        
    def __unicode__(self):
        return self.name
    
    
    
class TrainingSession(models.Model):
    thematic_area = models.ForeignKey(ThematicArea, null=True, blank=True, on_delete=models.CASCADE)
    training_reference = models.CharField(max_length=256, null=True, blank=True)
    trainer = models.ForeignKey(User, related_name='training_officer', null=True, blank=True, on_delete=models.CASCADE)
    is_external = models.BooleanField(default=False)
    external_trainer = models.ForeignKey(ExternalTrainer, null=True, blank=True, on_delete=models.CASCADE)
    topic = models.CharField(max_length=256, null=True, blank=True)
    descriprion = models.TextField(null=True, blank=True)
    cooperative = models.ForeignKey(Cooperative, null=True, blank=True, on_delete=models.CASCADE)
    coop_member = models.ManyToManyField(CooperativeMember, blank=True)
    gps_location = models.CharField(max_length=256, null=True, blank=True)
    training_start = models.DateTimeField()
    training_end = models.DateTimeField()
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'training_session'
        
    def __unicode__(self):
        return self.training_reference
    
    def duration(self):
        if self.training_start and self.training_end:
            start = "%s" % (self.training_start)
            end = "%s" % (self.training_end)
            time1 = datetime.datetime.strptime(start[:19],'%Y-%m-%d %H:%M:%S')
            time2 = datetime.datetime.strptime(end[:19],'%Y-%m-%d %H:%M:%S')
            difference = time2-time1
            return difference
    
    
 
class Visit(models.Model):
    coop_member = models.ForeignKey(CooperativeMember, on_delete=models.CASCADE)
    visit_date = models.DateField()
    reason = models.CharField(max_length=160)
    description = models.TextField(null=True, blank=True)
    gps_coodinates = models.CharField(max_length=256, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partner_visit'
        
    def __unicode__(self):
        return "%s" % self.coop_member
