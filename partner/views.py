# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User
from conf.utils import log_debug, log_error
from partner.models import *
from userprofile.models import AccessLevel
from partner.forms import PartnerForm, PartnerStaffForm

class ExtraContext(object):
    extra_context = {}
    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_partner']
        context['title'] = 'Country'
        context.update(self.extra_context)
        return context


class PartnerListView(ExtraContext, ListView):
    model = Partner


class PartnerCreateView(ExtraContext, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partner/partnercreate_form.html"
    success_url = reverse_lazy('partner:list')


class PartnerUpdateView(ExtraContext, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partner/partnercreate_form.html"
    success_url = reverse_lazy('partner:list')
    
    
class PartnerStaffListView(ExtraContext, ListView):
    model = PartnerStaff
    
    def get_queryset(self):
        qs = super(PartnerStaffListView, self).get_queryset()
        if not self.request.user.profile.is_union():
            partner = self.request.user.system_user.partner 
            qs = qs.filter(partner=partner) 
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PartnerStaffListView, self). get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        
        context['partner'] = Partner.objects.get(pk=pk)
        return context


class PartnerStaffCreateView(ExtraContext, CreateView):
    model = PartnerStaff
    form_class = PartnerStaffForm
    template_name = "partner/partnerstaffcreate_form.html"
    #success_url = reverse_lazy('partner:list')
    
    def form_invalid(self, form):
        print "form is invalid"
        return super(PartnerStaffCreateView, self).form_valid(form)
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        username =  form.cleaned_data.get('username')
        password =  form.cleaned_data.get('password')
        
        if PartnerStaff.objects.filter(phone_number=form.instance.phone_number).exists():
            form.add_error('phone_number', 'The Phone Number %s exists. Please provide another.' % form.instance.phone_number)
            return super(PartnerStaffCreateView, self).form_invalid(form) 
        
        try:
            user, created = User.objects.get_or_create(username=username, email='')
        except Exception as e:
            log_error()
            form.add_error('username', e)
            return super(PartnerStaffUpdateView, self).form_invalid(form) 
        if created:
            user.set_password(password)
            user.save()
        user.profile.access_level=AccessLevel.objects.get(name='PARTNER')
        user.save()
        form.instance.user = user
        
        try:
            return super(PartnerStaffCreateView, self).form_valid(form)
        except  Exception as e:
            log_error()
            form.add_error('', e)
            return super(PartnerStaffCreateView, self).form_invalid(form)
    
    def get_success_url(self, **kwargs):         
        return reverse_lazy('partner:staff_list', args = self.kwargs.get('pk'))
    
    def get_context_data(self, **kwargs):
        context = super(PartnerStaffCreateView, self). get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        
        context['partner'] = Partner.objects.get(pk=pk)
        return context
    
 
class PartnerStaffUpdateView(ExtraContext, UpdateView):
    model = PartnerStaff
    form_class = PartnerStaffForm
    template_name = "partner/partnerstaffcreate_form.html"
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        username = form.cleaned_data.get('username')
        try:
            user, created = User.objects.get_or_create(username=username, email='')
            user.profile.access_level=AccessLevel.objects.get(name='PARTNER')
            user.save()
            form.instance.user = user
        except Exception as e:
            log_error()
            form.add_error('', e)
            return super(PartnerStaffUpdateView, self).form_invalid(form)

        try:
            return super(PartnerStaffUpdateView, self).form_valid(form)
        except  Exception as e:
            log_error()
            form.add_error('', e)
            return super(PartnerStaffUpdateView, self).form_invalid(form)
    
    def get_success_url(self, **kwargs):         
        return reverse_lazy('partner:staff_list', args = self.kwargs.get('code'))
    
    def get_context_data(self, **kwargs):
        context = super(PartnerStaffUpdateView, self). get_context_data(**kwargs)
        pk = self.kwargs.get('code')
        
        context['partner'] = Partner.objects.get(pk=pk)
        return context

