# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import json
import xlrd
import datetime
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.encoding import smart_str
from django.db import transaction
from django.http import JsonResponse
from django.views.generic import View, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from conf.utils import log_debug, log_error, get_deleted_objects, get_consontant_upper
from conf.models import District, County, SubCounty
from coop.models import Cooperative, CooperativeContribution, CooperativeShareTransaction, \
    AnimalIdentification, TickControl, CooperativeSharePrice, CommonDisease, FarmerGroup, CooperativeRegistrationFee, \
    Clan
from coop.forms import CooperativeForm, CooperativeContributionForm, CooperativeShareTransactionForm, AnimalIdentificationForm,\
CooperativeSharePriceForm, CooperativeUploadForm, CommonDiseasesForm, FarmerGroupForm, CooperativeRegistrationFeeForm, ClanForm

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

def animal_identification(request):
    pass


class ClanListView(ListView):
    model = Clan
    fields = ['name']


class ClanCreateView(CreateView):
    model = Clan
    form_class = ClanForm
    success_url = reverse_lazy('coop:clan-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.date_joined = datetime.datetime.now()
        return super(ClanCreateView, self).form_valid(form)


class ClanUpdateView(UpdateView):
    model = Clan
    form_class = ClanForm
    success_url = reverse_lazy('coop:clan-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(ClanUpdateView, self).form_valid(form)


class ClanDeleteView(DeleteView):
    model = Clan
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('coop:clan-list')

    def get_context_data(self, **kwargs):
        #
        context = super(ClanDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context


#     end clan
    

class CooperativeListView(ListView):
    model = Cooperative
    fields = ['name', 'code', 'location']
    
    
class CooperativeCreateView(CreateView):
    model = Cooperative
    form_class = CooperativeForm
    success_url = reverse_lazy('coop:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.code = self.check_code(form)
        form.instance.date_joined = datetime.datetime.now()
        return super(CooperativeCreateView, self).form_valid(form)
    
    def check_code(self, form):
        code = get_consontant_upper(form.instance.name)
        q = Cooperative.objects.filter(code=code)
        if q.exists():
            count = q.count()
            q2 = Cooperative.objects.filter(code__contains=form.instance.name.upper()[:3])
            code = "%s%s" % (form.instance.name.upper()[:3], count+1)
            return code
        return get_consontant_upper(form.instance.name)
    
    
class CooperativeUpdateView(UpdateView):
    model = Cooperative
    form_class = CooperativeForm
    success_url = reverse_lazy('coop:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CooperativeUpdateView, self).form_valid(form)
    
    
class CooperativeDeleteView(DeleteView):
    model = Cooperative
    success_url = reverse_lazy('coop:list')

    def get_context_data(self, **kwargs):
        #
        context = super(CooperativeDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects']=deletable_objects
        context['model_count']=dict(model_count).items()
        context['protected']=protected
        #
        return context

class CooperativeSharePriceListView(ExtraContext, ListView):
    model = CooperativeSharePrice
    ordering = ['-create_date']
    extra_context = {'active': ['_coop_settings', '__share_price']}


class CooperativeUploadView(View):
    template_name = 'coop/upload_cooperative.html'
    
    def get(self, request, *arg, **kwargs):
        data = dict()
        data['form'] = CooperativeUploadForm
        return render(request, self.template_name, data)
    
    
    def post(self, request, *args, **kwargs):
        data = dict()
        form = CooperativeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']
            
            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet'])-1
            startrow = int(form.cleaned_data['row'])-1
            cooperative_col = int(form.cleaned_data['cooperative_col'])
            district_col = int(form.cleaned_data['district_col'])
            sub_county_col = int(form.cleaned_data['sub_county_col'])
            contact_person_col = int(form.cleaned_data['contact_person'])
            phone_number_col = int(form.cleaned_data['phone_number'])            
    
            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            cooperative_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i+1
                    cooperative = smart_str(row[cooperative_col].value).strip()
                    
                    if not re.search('^[A-Z\s\(\)\-\.]+$', cooperative, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Cooperative (row %d)' % \
                        (cooperative, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    district = smart_str(row[district_col].value).strip()
                    
                    if district:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', district, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid District (row %d)' % \
                            (district, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                        
                    sub_county = smart_str(row[sub_county_col].value).strip()
                    
                    if sub_county:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', sub_county, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Sub County (row %d)' % \
                            (sub_county, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    contact_person = smart_str(row[contact_person_col].value).strip()
                    if contact_person:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', contact_person, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Contact Person (row %d)' % \
                            (contact_person, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    phone_number = smart_str(row[phone_number_col].value).strip()
                    
                    if phone_number:
                        try:
                            phone_number = int(row[phone_number_col].value)
                        except Exception:
                            data['errors'] = '"%s" is not a valid Phone number (row %d)' % \
                            (phone_number, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                        
                        
                    q = {'cooperative': cooperative, 'district': district, 'sub_county':sub_county,
                         'contact_person': contact_person, 'phone_number': phone_number}
                    cooperative_list.append(q)
                    
                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})
            if cooperative_list:
                with transaction.atomic():
                    try:
                        do = None
                        sco = None
                        for c in cooperative_list:
                            cooperative = c.get('cooperative')
                            district = c.get('district')
                            sub_county = c.get('sub_county')
                            contact_person = c.get('contact_person')
                            phone_number = c.get('phone_number')
                            
                            if district:
                                dl = [dist for dist in District.objects.filter(name=district)]
                                do = dl[0] if len(dl)>0 else None
                            
                            if sub_county:
                                scl = [subc for subc in SubCounty.objects.filter(county__district__name=district, name=sub_county)]
                                sco = scl[0] if len(scl)>0 else None
                                
                            if not Cooperative.objects.filter(name=cooperative).exists():
                                code = self.check_code(cooperative)
                                Cooperative(
                                    name = cooperative,
                                    code = code,
                                    district = do,
                                    sub_county = sco,
                                    contact_person_name = contact_person,
                                    phone_number = phone_number,
                                    date_joined = datetime.datetime.now(),
                                    created_by = self.request.user
                                ).save()
                                
                        return redirect('coop:list')
                    except Exception as err:
                        log_error()
                        data['error'] = err
                
        data['form'] = form
        return render(request, self.template_name, data)
    
    def check_code(self, cooperative):
        code = get_consontant_upper(cooperative)
        q = Cooperative.objects.filter(code=code)
        if q.exists():
            coop = Cooperative.objects.all()
            return "%s%s" % (cooperative.strip().upper()[:3], coop.count())
        return get_consontant_upper(cooperative)


    
class CooperativeSharePriceCreateView(CreateView):
    model = CooperativeSharePrice
    form_class = CooperativeSharePriceForm
    template_name = "coop/cooperativeshareprice_form.html"
    success_url = reverse_lazy('coop:share_price_list')
    
    def get_form_kwargs(self):
        kwargs = super(CooperativeSharePriceCreateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CooperativeSharePriceCreateView, self).form_valid(form)


class CooperativeSharePriceUpdateView(UpdateView):
    model = CooperativeSharePrice
    form_class = CooperativeSharePriceForm
    success_url = reverse_lazy('coop:share_price_list')
    
    def get_form_kwargs(self):
        kwargs = super(CooperativeSharePriceUpdateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CooperativeSharePriceUpdateView, self).form_valid(form)


#
class CooperativeRegistrationFeeListView(ExtraContext, ListView):
    model = CooperativeRegistrationFee
    ordering = ['-create_date']
    extra_context = {'active': ['_coop_settings', '__fee']}


class CooperativeRegistrationFeeCreateView(CreateView):
    model = CooperativeRegistrationFee
    form_class = CooperativeRegistrationFeeForm
    template_name = "coop/cooperativefee_form.html"
    success_url = reverse_lazy('coop:fee_list')

    def get_form_kwargs(self):
        kwargs = super(CooperativeRegistrationFeeCreateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CooperativeRegistrationFeeCreateView, self).form_valid(form)


class CooperativeRegistrationFeeUpdateView(UpdateView):
    model = CooperativeRegistrationFee
    form_class = CooperativeRegistrationFeeForm
    template_name = "coop/cooperativefee_form.html"
    success_url = reverse_lazy('coop:fee_list')

    def get_form_kwargs(self):
        kwargs = super(CooperativeRegistrationFeeUpdateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CooperativeRegistrationFeeUpdateView, self).form_valid(form)

#
class CooperativeContributionListView(ListView):
    model = CooperativeContribution
    

class CooperativeContributionCreateView(CreateView):
    model = CooperativeContribution
    form_class = CooperativeContributionForm
    success_url = reverse_lazy('coop:contribution_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        bal_before = form.instance.cooperative.contribution_total
        bal_after = bal_before + form.instance.amount
        form.instance.cooperative.contribution_total = bal_after
        form.instance.cooperative.save()
        form.instance.new_balance = bal_after
        return super(CooperativeContributionCreateView, self).form_valid(form)
    
    
class CooperativeContributionUpdateView(UpdateView):
    model = CooperativeContribution
    form_class = CooperativeContributionForm
    success_url = reverse_lazy('coop:contribution_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeContribution.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative.contribution_total
        deducted = acc_bal - cont.amount
        final = deducted + form.instance.amount
        form.instance.cooperative.contribution_total = final
        form.instance.cooperative.save()
        form.instance.new_balance = final
        return super(CooperativeContributionUpdateView, self).form_valid(form)
    
    
class CooperativeShareTransactionListView(ExtraContext, ListView):
    model = CooperativeShareTransaction
    extra_context = {'active': ['_coop_shares']}
    
    
class CooperativeShareTransactionCreateView(CreateView):
    model = CooperativeShareTransaction
    form_class = CooperativeShareTransactionForm
    success_url = reverse_lazy('coop:share_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        bal_before = form.instance.cooperative.shares
        bal_after = bal_before + form.instance.shares_bought
        form.instance.cooperative.shares = bal_after
        form.instance.cooperative.save()
        form.instance.new_shares = bal_after
        return super(CooperativeShareTransactionCreateView, self).form_valid(form)
    
    
class CooperativeShareTransactionUpdateView(UpdateView):
    model = CooperativeShareTransaction
    form_class = CooperativeShareTransactionForm
    success_url = reverse_lazy('coop:share_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeShareTransaction.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative.shares
        deducted = acc_bal - cont.shares_bought
        final = deducted + form.instance.shares_bought
        form.instance.cooperative.shares = final
        form.instance.cooperative.save()
        form.instance.new_shares = final
        return super(CooperativeShareTransactionUpdateView, self).form_valid(form)
    
    
class CooperateCommonDiseaseCreateView(CreateView):
    model = CommonDisease
    form_class = CommonDiseasesForm
    success_url = reverse_lazy('coop:disease_list')
    
    def get_context_data(self, **kwargs):
        context = super(CooperateCommonDiseaseCreateView, self).get_context_data(**kwargs)
        context['active']= ['_coop_settings', '__disease']
        return context
    

class CooperateCommonDiseaseUpdateView(UpdateView):
    model = CommonDisease
    form_class = CommonDiseasesForm
    success_url = reverse_lazy('coop:disease_list')
    
    
class CooperateCommonDiseaseListView(ListView):
    model = CommonDisease


class FarmerGroupListView(ListView):
    model = FarmerGroup
    fields = ['cooperative', 'name']


class FarmerGroupCreateView(CreateView):
    model = FarmerGroup
    form_class = FarmerGroupForm
    success_url = reverse_lazy('coop:fg_list')


class FarmerGroupUpdateView(UpdateView):
    model = FarmerGroup
    form_class = FarmerGroupForm
    success_url = reverse_lazy('coop:fg_list')



class FarmerGroupDeleteView(DeleteView):
    model = FarmerGroup
    success_url = reverse_lazy('coop:fg_list')

    def get_context_data(self, **kwargs):
        #
        context = super(FarmerGroupDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context


def ajax_load_fee(request):
    cooperative = request.GET.get('cooperative')
    fee = 0
    rf = CooperativeRegistrationFee.objects.filter(cooperative=cooperative).order_by('-create_date')
    if rf.exists():
        fee =  rf[0].price
    return JsonResponse({"fee": fee})