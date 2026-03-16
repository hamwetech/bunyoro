# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import transaction
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.generic import View, ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.forms.formsets import formset_factory, BaseFormSet

from conf.utils import generate_alpanumeric, generate_numeric, log_debug, log_error
from product.models import Product, ProductVariation, ProductVariationPrice
from operations.forms import PurchaseForm, PurchaseProductForm, PurchasePrefixFormSet
from coop.models import CooperativeMember
from operations.models import PartnerPurchaseTransaction, MemberPurchaseTransaction, PurchasePaymentLog


class PurchaseCreateView(View):
    template_name = 'operations/purchase.html'
    active = ['_op']
    
    def get(self, request, *args, **kwargs):
        initial = None
        form = PurchaseForm
        product_form = formset_factory(PurchaseProductForm, formset=PurchasePrefixFormSet)
        product_formset = product_form(prefix='product', initial=initial)
        if request.GET.get('per_kilo'):
            return self.get_price_per_kilo(request.GET.get('per_kilo'))
        data = {
            'form': form,
            'product_formset': product_formset,
            'active': self.active
        }
        return render(request, self.template_name, data)
    
    
    def post(self, request, *args, **kwargs):
        initial = None
        form = PurchaseForm(request.POST)
        product_form = formset_factory(PurchaseProductForm, formset=PurchasePrefixFormSet)
        product_formset = product_form(request.POST, prefix='product', initial=initial)
        if request.GET.get('per_kilo'):
            return self.get_price_per_kilo(request.GET.get('per_kilo'))
        
        if form.is_valid() and product_formset.is_valid():
            try:
                with transaction.atomic():
                    'Determine the user type'
                    al = 'UNDEFINED'
                    if request.user.profile.is_cooperative():
                        al = 'COOPERATIVE'
                    if request.user.profile.is_partner():
                        al = 'PARTNER'
                        
                    'Save Purchase transaction.'
                    purchase = form.save(commit=False)
                    purchase.created_by = request.user
                    purchase.purchaser = al
                    purchase.transaction_id = generate_alpanumeric()
                    purchase.save()
                    
                    total_amount = 0
                    total_paid = 0
                    
                    'Save Products'
                    for product in product_formset:
                        p = product.save(commit=False)
                        p.purchase = purchase
                        p.save()
                        total_amount += p.total_amount
                        total_paid += p.paid_amount
                    
                    'Update Purchase total Purchase and Paid Amount'
                    purchase.total_amount = total_amount
                    purchase.paid_amount = total_paid
                    purchase.save()
                    
                    'if Payment made save here'
                    if total_paid > 0:
                        PurchasePaymentLog.objects.create(
                            purchase = purchase,
                            transaction_id = generate_numeric(size=8),
                            amount = total_paid,
                            transaction_type = '',
                            transaction_date = purchase.transaction_date
                        )
                    
                    'Save the Transation Owner'
                    if al == 'PARTNER':
                        PartnerPurchaseTransaction.objects.create(
                            purchase = purchase,
                            partner_staff = request.user.system_user
                        )
                    
                    'If Member save Member Transaction'
                    member = CooperativeMember.objects.filter(phone_number=purchase.seller_msisdn)
                    if member.exists():
                        member = member[0]
                        MemberPurchaseTransaction.objects.create(
                            purchase = purchase,
                            member = member
                        )
                    return redirect('op:purchase_list')
            except Exception as e:
                log_error()
        data = {
            'form': form,
            'product_formset': product_formset,
            'active': self.active
        }
        return render(request, self.template_name, data)
    
    def get_price_per_kilo(self, id):
        price = 0
        pv = ProductVariationPrice.objects.filter(breed__id=id)
        if pv.exists():
            pv = pv[0]
            price = pv.price
        return JsonResponse({'price': price})
    

class PurchaseListView(ListView):
    model = PartnerPurchaseTransaction
    
    def get_queryset(self):
        qs = super(PurchaseListView, self).get_queryset()
        return qs
    
    def get_context(self, **kwargs):
        context = super(PurchaseListView, self).get_context_data(**kwargs)
        return context