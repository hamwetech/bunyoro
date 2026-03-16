# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import magic
import re
import xlrd
import xlwt
import time
from datetime import datetime
import json
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, CharField, Max, Value as V
from django.db.models.functions import Concat
from django.utils.encoding import smart_str
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.views.generic import View, ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormMixin, FormView
from django.forms.formsets import formset_factory, BaseFormSet

from messaging.utils import sendSMS
from coop.utils import sendMemberSMS
from conf.utils import log_debug, log_error, internationalize_number, generate_alpanumeric, float_to_intstring, genetate_uuid4, get_deleted_objects,\
get_message_template as message_template
from coop.models import *
from activity.models import TrainingAttendance
from product.models import Product, ProductVariation, ProductUnit
from coop.forms import *
from account.models import Account, AccountTransaction
from api.OKOTransactions import OKOTransaction

from payment.HamwePay import HamwePay

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member']
        context['title'] = 'Coop'
        context.update(self.extra_context)
        return context


class MemberDeleteView(ExtraContext, DeleteView):
    model = CooperativeMember
    success_url = reverse_lazy('coop:member_list')
    
    def get_context_data(self, **kwargs):
        #
        context = super(MemberDeleteView, self).get_context_data(**kwargs)
        #
        
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects']=deletable_objects
        context['model_count']=dict(model_count).items()
        context['protected']=protected
        #
        return context


class MemberCreateView(ExtraContext, CreateView):
    template_name = 'coop/memberprofile_form.html'
    model = CooperativeMember
    form_class = MemberProfileForm
    success_url = reverse_lazy('coop:member_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberCreateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.member_id = self.generate_member_id(form.instance.cooperative)
            form.instance.create_by = self.request.user
            member = super(MemberCreateView, self).form_valid(form)
        except Exception as e:
            # form.add_error(None, 'The Phone Number %s exists. Please provide another.' % form.instance.phone_number)
            import traceback
            print(traceback.format_exc())
            form.add_error(None, e)
            return super(MemberCreateView, self).form_invalid(form)
        try:
            
            message = message_template().member_registration
            if message:
                if re.search('<NAME>', message):
                    if member.surname:
                        message = message.replace('<NAME>', '%s %s' % (member.surname.title(), member.first_name.title()))
                    message = message.replace('<COOPERATIVE>', member.cooperative.name)
                    message = message.replace('<IDNUMBER>', member.member_id)
                sendMemberSMS(request, member, message)
        except Exception as e:
            log_error()
            pass
        return member
    
    def generate_member_id(self, cooperative):
        member = CooperativeMember.objects.all()
        count = member.count() + 1
        
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
        # fint = "%04d"%count
        # idno = str(cooperative.code)+yr+fint
        # member = member.filter(member_id=idno)
        if cooperative:
            idno = self.check_id(member, cooperative, count, yr)
            log_debug("Cooperative %s code is %s" % (cooperative.code, idno))
        else:
            idno = self.check_id_nc(member, count, yr)
        return idno
    
    def check_id(self, member, cooperative, count, yr):
        fint = "%04d"%count
        idno = str(cooperative.code)+yr+fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            #print "iteration count %s" % count
            return self.check_id(member, cooperative, count, yr)
        return idno

    def check_id_nc(self, member, count, yr):
        rnd = generate_alpanumeric(size=3).upper()
        fint = "%04d"%count
        idno = rnd+yr+fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            #print "iteration count %s" % count
            return self.check_id_nc(member, count, yr)
        return idno


class MemberUpdateView(ExtraContext, UpdateView):
    template_name = 'coop/memberprofile_form.html'
    model = CooperativeMember
    form_class = MemberProfileForm
    success_url = reverse_lazy('coop:member_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberUpdateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    
def save_transaction(params):
        amount = params.get('amount')
        member = params.get('member')
        transaction_reference = params.get('transaction_reference')
        transaction_type = params.get('transaction_type')
        entry_type = params.get('entry_type')
        
        bal_before = 0
        tq = MemberTransaction.objects.all().order_by('-id')
        if tq.exists():
            bal_before = tq[0].balance_after
        new_bal = amount + bal_before
        MemberTransaction.objects.create(
            member = member,
            transaction_type = transaction_type,
            entry_type = entry_type,
            transaction_reference = transaction_reference, 
            balance_before = bal_before,
            amount = amount,
            balance_after = new_bal
        )
        CooperativeMember.objects.filter(pk=member.id).update(collection_amount=new_bal)
        
               
def load_villages(request):
    sub_county_id = request.GET.get('sub_county')
    villages = Parish.objects.filter(sub_county=sub_county_id).order_by('name')
    return render(request, 'coop/village_dropdown_list_options.html', {'villages': villages})


def load_coop_members(request):
    cooperative_id = request.GET.get('cooperative')
    members = dict()
    if cooperative_id: 
        members = CooperativeMember.objects.filter(cooperative=cooperative_id).order_by('first_name')
    return render(request, 'coop/member_dropdown_list_options.html', {'members': members})


class MemberUploadExcel(ExtraContext, View):
    template_name = 'coop/upload_member.html'
    
    def get(self, request, *args, **kwargs):
        data = dict()
        data['form'] =  MemberUploadForm
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs):
        data = dict()
        form = MemberUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']
            
            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet'])-1
            startrow = int(form.cleaned_data['row'])-1
            
            farmer_name_col = int(form.cleaned_data['farmer_name_col'])
            identification_col = int(form.cleaned_data['identification_col'])
            gender_col = int(form.cleaned_data['gender'])
            date_of_birth_col = int(form.cleaned_data['date_of_birth_col'])
            phone_number_col = int(form.cleaned_data['phone_number_col'])
            role_col = int(form.cleaned_data['role_col'])
            acreage_col = int(form.cleaned_data['acreage_col'])
            # cotton_col = int(form.cleaned_data['cotton_col'])
            # soya_col = int(form.cleaned_data['soya_col'])
            # soghum_col = int(form.cleaned_data['soghum_col'])
            cooperative_col = int(form.cleaned_data['cooperative_col'])
            district_col = int(form.cleaned_data['district_col'])
            county_col = int(form.cleaned_data['county_col'])
            sub_county_col = int(form.cleaned_data['sub_county_col'])
            parish_col = int(form.cleaned_data['parish_col'])
            village_col = int(form.cleaned_data['village_col'])
            
            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            member_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i+1
                    
                    farmer_name = smart_str(row[farmer_name_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', farmer_name, re.IGNORECASE):
                        if (i+1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Farmer (row %d)' % \
                        (farmer_name, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    gender = smart_str(row[gender_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', gender, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Gender (row %d)' % \
                        (gender, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})

                    identification = smart_str(row[identification_col].value).strip()
                    if identification:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', gender, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Identification Number (row %d)' % \
                            (identification, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
               
                    date_of_birth = (row[date_of_birth_col].value)
                    if date_of_birth:
                        try:
                            #print(date_of_birth)
                            date_str = datetime(*xlrd.xldate_as_tuple(date_of_birth, book.datemode))
                            date_of_birth = date_str.strftime("%Y-%m-%d")
                        except Exception as e:
                            data['errors'] = '"%s" is not a valid Date of Birth (row %d): %s' % \
                            (date_of_birth, i+1, e)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                   
                    
                    phone_number = (row[phone_number_col].value)
                    if phone_number:
                        try:
                            phone_number = int(phone_number)
                        except Exception as e:
                            ##print e
                            phone_number = None

                        if phone_number:
                            if not re.search('^[0-9]+$', str(phone_number), re.IGNORECASE):
                                data['errors'] = '"%s" is not a valid Phone Number (row %d)' % \
                                (phone_number, i+1)
                                return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                
                    
                    role = smart_str(row[role_col].value).strip()
                    if role:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', role, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Role (row %d)' % \
                            (role, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    acreage = smart_str(row[acreage_col].value).strip()
                    if not re.search('^[0-9\.]+$', acreage, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Acreage (row %d)' % \
                        (cotton, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    # soya = smart_str(row[soya_col].value).strip()
                    # if not re.search('^[0-9\.]+$', soya, re.IGNORECASE):
                    #     data['errors'] = '"%s" is not a valid Soya Acreage (row %d)' % \
                    #     (soya, i+1)
                    #     return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    #
                    # soghum = smart_str(row[soghum_col].value).strip()
                    # if not re.search('^[0-9\.]+$', soghum, re.IGNORECASE):
                    #     data['errors'] = '"%s" is not a valid Soghum Acreage (row %d)' % \
                    #     (soya, i+1)
                    #     return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
        
                    
                    cooperative = smart_str(row[cooperative_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', cooperative, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Cooperative (row %d)' % \
                        (cooperative, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
        
                    try:
                        cooperative = Cooperative.objects.get(name=cooperative)
                    except Exception as e:
                        log_error()
                        data['errors'] = 'Cooperative "%s" Not found (row %d)' % \
                        (cooperative, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
        
                    
                    district = smart_str(row[district_col].value).strip()
                    
                    if district:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', district, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid District (row %d)' % \
                            (district, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    county = smart_str(row[county_col].value).strip()
                    
                    if county:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', county, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid County (row %d)' % \
                            (county, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})    
                    
                    sub_county = smart_str(row[sub_county_col].value).strip()
                    
                    if sub_county:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', sub_county, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Sub County (row %d)' % \
                            (sub_county, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    parish = smart_str(row[parish_col].value).strip()
                    
                    if parish:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', parish, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Parish (row %d)' % \
                            (parish, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                   
                    village = smart_str(row[village_col].value).strip()
                    
                    if village:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', village, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Village (row %d)' % \
                            (village, i+1)
                            return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                    
                    q = {
                         'farmer_name': farmer_name,
                         'identification': identification,
                         'gender': gender,
                         'date_of_birth': date_of_birth,
                         'phone_number': phone_number,
                         'role': role,
                         'acreage': acreage,
                         # 'soya': soya,
                         # 'soghum': soghum,
                         'cooperative': cooperative,
                         'district': district,
                         'county':county,
                         'sub_county':sub_county,
                         'parish': parish,
                         'village': village
                    }
                    member_list.append(q)
                
                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})
            if member_list:
                with transaction.atomic():
                    try:
                        do = None
                        sco = None
                        co = None
                        po = None
                        for c in member_list:
                            name = c.get('farmer_name').split(' ')
                            surname = name[0]
                            first_name = name[1] if len(name) > 1 else None
                            other_name = name[2] if len(name) > 2 else None
                            identification = c.get('identification')
                            cooperative = c.get('cooperative')
                            district = c.get('district')
                            sub_county = c.get('sub_county')
                            county = c.get('county')
                            parish = c.get('parish')
                            village = c.get('village')
                            phone_number = c.get('phone_number')
                            acreage = c.get('acreage') if c.get('acreage') != '' else 0
                            # soya = c.get('soya') if c.get('soya') != '' else 0
                            # soghum = c.get('soghum') if c.get('soghum') != '' else 0
                            phone_number = c.get('phone_number')
                            gender = c.get('gender')
                            role = c.get('role')
                            date_of_birth = c.get('date_of_birth') if c.get('date_of_birth') != '' else None
    
                            if district:
                                dl = [dist for dist in District.objects.filter(name__iexact=district)]
                                do = dl[0] if len(dl)>0 else None
                            
                            
                            if county:
                                cl = [c for c in County.objects.filter(district__name=district, name=county)]
                                co = cl[0] if len(cl)>0 else None
                            
                            if sub_county:
                                scl = [subc for subc in SubCounty.objects.filter(county__name=county, name=sub_county)]
                                sco = scl[0] if len(scl)>0 else None
                                
                            if parish:
                                pl = [p for p in Parish.objects.filter(sub_county__name=sub_county, name=parish)]
                                po = pl[0] if len(pl)>0 else None
                                
                            if not CooperativeMember.objects.filter(first_name=first_name, surname=surname, phone_number=phone_number).exists():
                                member = CooperativeMember.objects.create(
                                    cooperative = cooperative,
                                    surname = surname,
                                    first_name = first_name,
                                    other_name = other_name,
                                    id_number = identification,
                                    gender = gender,
                                    member_id = self.generate_member_id(cooperative),
                                    date_of_birth = date_of_birth,
                                    phone_number = phone_number if phone_number != '' else None,
                                    district = do,
                                    county = co,
                                    sub_county = sco,
                                    parish = po,
                                    village = village,
                                    coop_role = role.title(),
                                    land_acreage = acreage,
                                    # soya_beans_acreage = soya,
                                    # soghum_acreage = soghum,
                                    create_by = request.user
                                )
                                
                                message = message_template().member_registration
                                #if message:
                                #    if re.search('<NAME>', message):
                                #        if member.surname:
                                #            message = message.replace('<NAME>', '%s %s' % (member.surname.title(), member.first_name.title()))
                                #        message = message.replace('<COOPERATIVE>', member.cooperative.name)
                                #        message = message.replace('<IDNUMBER>', member.member_id)
                                #    sendMemberSMS(request, member, message)
                                                    
                        return redirect('coop:member_list')
                    except Exception as err:
                        log_error()
                        data['error'] = err
                
        data['form'] = form
        return render(request, self.template_name, data)
    
    
    def generate_member_id(self, cooperative):
        member = CooperativeMember.objects.all()
        count = member.count() + 1
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
        fint = "%04d"%count
        idno = str(cooperative.code)+yr+fint
        log_debug("Cooperative %s code is %s" % (cooperative.code, idno))
        return idno
    

class CooperativeMemberListView(ExtraContext, ListView):
    model = CooperativeMember
    template_name = 'coop/cooperativemember_list.html'
    ordering = ['-id']
    
    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(CooperativeMemberListView, self).dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super(CooperativeMemberListView, self).get_queryset()
        card_number = self.request.GET.get('card_number')
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        create_by = self.request.GET.get('create_by')

        if self.request.user.profile.is_partner():
            queryset = queryset.all()
        elif not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            queryset = queryset.filter(cooperative=cooperative)
        if card_number:
            queryset = queryset.filter(consumer_device_id__icontains=card_number)
        if msisdn:
            queryset = queryset.filter(phone_number='%s' % msisdn)
        if name:
            #name=Concat('surname',V(' '),'first_name',V(' '),'other_name')
            queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
            #queryset = queryset.filter(Concat(surname,V(' '),first_name,V(' '),other_name)=name)
        if coop:
            queryset = queryset.filter(cooperative__id=coop)
        if role:
            queryset = queryset.filter(coop_role=role)
        if district:
            queryset = queryset.filter(district__id=district)
        if create_by:
            queryset = queryset.filter(create_by__profile__id=create_by)
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(CooperativeMemberListView, self).get_context_data(**kwargs)
        context['form'] = MemberProfileSearchForm(self.request.GET, request=self.request)
        qr = self.get_queryset()
        of = qr.filter(own_phone=True)
        hmm = qr.filter(has_mobile_money=True)
        context['own_phone'] = of.count()
        context['has_mobile_money'] = hmm.count()
        return context
    
    def download_file(self, *args, **kwargs):
        
        _value = []
        columns = []
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        create_by = self.request.GET.get('create_by')

        
        profile_choices = ['id','cooperative__name', 'farmer_group__name', 'member_id', 'surname', 'first_name', 'other_name',
                               'date_of_birth', 'gender', 'id_number','phone_number','is_refugee', 'is_handicap', 'app_id', 'cpk_rid', 'consent_id', 'consumer_device_id', 'create_wallet', 'has_flexipay',
                               'district__name','sub_county__name','village','address','gps_coodinates',
                               'coop_role','land_acreage', 'bee_hives', 'product',
                               'collection_amount','collection_quantity', 'paid_amount', 'create_date',  'create_by__username']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        #Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that 
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')
        
        # The response also has additional Content-Disposition header, which contains 
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=CommunityPassMembers_%s.xls' % datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create object for the Workbook which is under xlwt library.
        workbook = xlwt.Workbook()
        
        # By using Workbook object, add the sheet with the name of your choice.
        worksheet = workbook.add_sheet("Members")

        row_num = 0
        style_string = "font: bold on; borders: bottom dashed"
        style = xlwt.easyxf(style_string)

        for col_num in range(len(columns)):
            # For each cell in your Excel Sheet, call write function by passing row number, 
            # column number and cell data.
            worksheet.write(row_num, col_num, columns[col_num], style=style)
        
        
        _members = CooperativeMember.objects.values(*profile_choices).all()
        
        if msisdn:
            _members = _members.filter(phone_number='%s' % msisdn)
        if name:
            _members = _members.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
        if coop:
            _members = _members.filter(cooperative__id=coop)
        if role:
            _members = _members.filter(coop_role=role)
        if district:
            _members = _members.filter(district__id=district)
        if create_by:
            _members = _members.filter(create_by__profile__id=create_by)
        
        for m in _members:
            
            
            row_num += 1
            # ##print profile_choices
            row = []
            # row = [m['%s' % x]  if 'create_date' not in x else m['%s' % x].strftime('%d-%m-%Y %H:%M:%S') if 'village' not in x else self.get_village(m['%s' % x]) if 'date_of_birth' not in x else m['%s' % x].strftime('%d-%m-%Y')  if m.get('%s' % x) else ""  for x in profile_choices]
            for x in profile_choices:
                if m.get('%s' % x):
                    if 'create_date' in x:
                        row.append(m['%s' % x].strftime('%d-%m-%Y %H:%M:%S'))
                    elif 'date_of_birth' in x:
                        row.append(m['%s' % x].strftime('%d-%m-%Y'))
                    elif 'village' in x:
                        row.append(self.get_village(m['%s' % x]))
                    else:
                        row.append(m['%s' % x])
                else:
                    row.append("")

            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response

    def get_village(self, id):
        try:
            village = Village.objects.get(pk=id)
            village = village.name
        except Exception as e:
            village = ""
        print(village)
        return village
    
    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces :
            # Check if string is in the main string
            if elem in mainString :
                # Replace the string
                mainString = mainString.replace(elem, newString)
        
        return  mainString


class ImageQRCodeDownloadView(View):
    def get(self, request, *args, **kwargs):
        try:
            pk = self.kwargs.get('pk')
            qs = CooperativeMember.objects.get(pk=pk)
            image = qs.get_qrcode()
            ##print image.path
            image_buffer = open(image.path, "rb").read()
            content_type = magic.from_buffer(image_buffer, mime=True)
            response = HttpResponse(image_buffer, content_type=content_type);
            response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(image.path)
            return response
        except Exception:
            log_error()
            return redirect('coop:member_list') 


class DeprecatedDownloadExcelMemberView(View):
    template_name = 'coop/download_member.html'
    
    def get(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm(request.POST)
        if form.is_valid():
            _value = []
            profile = form.cleaned_data.get('profile')
            # farm = form.cleaned_data.get('farm')
            # deworming = form.cleaned_data.get('deworming')
            # breed = form.cleaned_data.get('breed')
            # bull_herd = form.cleaned_data.get('bull_herd')
            # cow_herd = form.cleaned_data.get('cow_herd')
            # member_supply = form.cleaned_data.get('member_supply')
            _value += profile
            # _value+= farm
            # _value += deworming
            # _value += breed
            # _value += bull_herd
            # _value += cow_herd
            # _value += member_supply
            if len(profile) > 0:
                _members = CooperativeMember.objects.values(*[x for x in profile]).all()
                for m in _members:
                    if len(farm) > 0:
                        _biz = CooperativeMemberBusiness.objects.values(*[x for x in farm]).filter(cooperative_member=m)
                    if len(deworming) > 0:
                        _deworm = DewormingSchedule.objects.values(*[x for x in deworming]).filter(cooperative_member=m)
                    if len(breed) > 0:
                        _breeds = CooperativeMemberProductDefinition.objects.values(*[x for x in deworming]).filter(cooperative_member=m)
                    if len(bull_herd) > 0:
                        _bulls = CooperativeMemberHerdMale.objects.values(*[x for x in bull_herd]).filter(cooperative_member=m)
                    if len(cow_herd) > 0:
                        _cows = CooperativeMemberHerdFemale.objects.values(*[x for x in cow_herd]).filter(cooperative_member=m)
                    if len(member_supply) > 0:
                        deworm = CooperativeMemberSupply.objects.values(*[x for x in member_supply]).filter(cooperative_member=m)
                
            raise Exception(len(farm))
        return render(request, self.template_name, {'form': form})


class DownloadExcelMemberView(View):
    template_name = 'coop/download_member.html'
    
    def get(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = DownloadMemberOptionForm(request.POST)
        if form.is_valid():
            _value = []
            profile = form.cleaned_data.get('profile')
            farm = form.cleaned_data.get('farm')
            herd = form.cleaned_data.get('herd')
            member_supply = form.cleaned_data.get('member_supply')
            columns = []
            
            profile_choices = ['id', 'farmer_group__name', 'member_id', 'surname', 'first_name', 'other_name',
                               'date_of_birth', 'gender', 'maritual_status','phone_number','email',
                               'district__name','sub_county__name','village','address','gps_coodinates',
                               'coop_role', 'land_acreage','product','shares',
                               'collection_amount','collection_quantity', 'gps_coodinates', 'create_by__username']
            
            farm_choices = ['business_name', 'farm_district__name','farm_sub_county__name', 'gps_coodinates',
                            'size', 'fenced', 'paddock','water_source',
                            'animal_identification','common_diseases','other_animal_diseases','tick_control']
    
            male_herd = ['adults', 'bullocks', 'calves']
            female_herd = ['f_adults', 'heifers', 'f_calves']
            member_supply_choice = ['nearest_market','product_average_cost','price_per_kilo','probable_sell_month',
                              'probable_sell_month', 'sell_to_cooperative_society']
            
            columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
            if farm:
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in farm_choices]
                columns += ['Deworm Schedule']
            if herd:
                columns += ['Breeds']
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in male_herd]
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in female_herd]
            if member_supply:
                columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in member_supply_choice]
            #Gather the Information Found
            # Create the HttpResponse object with Excel header.This tells browsers that 
            # the document is a Excel file.
            response = HttpResponse(content_type='application/ms-excel')
            
            # The response also has additional Content-Disposition header, which contains 
            # the name of the Excel file.
            response['Content-Disposition'] = 'attachment; filename=DigiexMembers_%s.xls' % datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Create object for the Workbook which is under xlwt library.
            workbook = xlwt.Workbook()
            
            # By using Workbook object, add the sheet with the name of your choice.
            worksheet = workbook.add_sheet("Members")

            row_num = 0
            style_string = "font: bold on; borders: bottom dashed"
            style = xlwt.easyxf(style_string)

            for col_num in range(len(columns)):
                # For each cell in your Excel Sheet, call write function by passing row number, 
                # column number and cell data.
                worksheet.write(row_num, col_num, columns[col_num], style=style)
            
            if profile:
                _members = CooperativeMember.objects.values(*profile_choices).all()
                
                for m in _members:
                    
                    if farm:
                        _biz = CooperativeMemberBusiness.objects.values(*farm_choices).filter(cooperative_member=m['id'])
                        _deworm = DewormingSchedule.objects.values('deworm_date','dewormer').filter(cooperative_member=m['id'])
                    if herd:
                        _breeds = CooperativeMemberProductDefinition.objects.filter(cooperative_member=m['id'])
                        _bulls = CooperativeMemberHerdMale.objects.values(*male_herd).filter(cooperative_member=m['id'])
                        _cows = CooperativeMemberHerdFemale.objects.values(*female_herd).filter(cooperative_member=m['id'])
                    if member_supply:
                        _member_supply = CooperativeMemberSupply.objects.values(*member_supply_choice).filter(cooperative_member=m['id'])
                    
                    row_num += 1
                    row = [m['%s' % x] for x in profile_choices]
                    if farm:
                        if _biz.exists():
                            row += [_biz[0]['%s' % x] for x in farm_choices]
                        if _deworm.exists():
                            row += [','.join(['%s | %s' % (dw['deworm_date'], dw['dewormer']) for dw in _deworm])]
                    if herd:
                        if _breeds.exists():
                            row += ['|'.join([brd.name for brd in _breeds[0].product_variation.all()])]
                        if _bulls.exists():
                            row += [_bulls[0]['%s' % x] for x in male_herd]
                        if _cows.exists():
                            row += [_cows[0]['%s' % x] for x in female_herd]
                    if member_supply:
                        if _member_supply.exists():
                            row += [_member_supply[0]['%s' % x] for x in member_supply_choice]
                    for col_num in range(len(row)):
                        worksheet.write(row_num, col_num, row[col_num])
                workbook.save(response)
                return response
                                        
            
        return render(request, self.template_name, {'form': form})

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces :
            # Check if string is in the main string
            if elem in mainString :
                # Replace the string
                mainString = mainString.replace(elem, newString)
        
        return  mainString


class SendCommunicationView(View):
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SendCommunicationView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        msisdn = self.request.GET.get('phone_number')
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        role = self.request.GET.get('role')
        district = self.request.GET.get('district')
        jres = {'status': 'error', 'message': 'Unknown Error! Message not sent. Contact Admin.'}
        try:
            queryset =  CooperativeMember.objects.all()
            if not request.user.profile.is_union():
                queryset = queryset.filter(cooperative = request.user.cooperative_admin.cooperative)
            response = ""
            if msisdn:
                queryset = queryset.filter(phone_number='%s' % msisdn)
                response += "Phone Number " + msisdn
            if name:
                queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
                response += " Name "
            if coop:
                queryset = queryset.filter(cooperative__id=coop)
                c = Cooperative.objects.get(pk=coop)
                response += " Cooperative "+c.name
            if role:
                queryset = queryset.filter(coop_role=role)
                response += " Role " + role
            if district:
                queryset = queryset.filter(district__id=district)
                d = District.objects.get(pk=district)
                response += " District " + d.name    
            response += "<div>Total Messages %s</div>" % queryset.count()
            jres = {'status': 'success', 'message': response}
        except Exception:
            log_error()
            jres = {'status': 'error', 'message': 'Error! Messages not Sent.'}
            
        return JsonResponse(jres)
    
    def post(self, request,  *args, **kwargs):
        ##print " Message: %s" % (self.request.body)
        body_unicode = self.request.body.decode('utf-8')
        data = json.loads(body_unicode)
        
        msisdn = data.get('phone_number')
        name = data.get('name')
        coop = data.get('cooperative')
        role = data.get('role')
        district = data.get('district')
        jres = {'status': 'error', 'message': 'Unknown Error! Message not sent. Contact Admin.'}
        
        try:
            queryset =  CooperativeMember.objects.all()
            if not request.user.profile.is_union():
                queryset = queryset.filter(cooperative = request.user.cooperative_admin.cooperative)
            if msisdn:
                queryset = queryset.filter(phone_number='%s' % msisdn)
            if name:
                queryset = queryset.filter(Q(surname__icontains=name)|Q(first_name__icontains=name)|Q(other_name=name))
            if coop:
                queryset = queryset.filter(cooperative__id=coop)
            if role:
                queryset = queryset.filter(coop_role=role)
            if district:
                queryset = queryset.filter(district__id=district)
            
            for q in queryset:
                count = 0
                message = data.get('message')
                msisdn = q.phone_number
                if re.search('<NAME>', message):
                    if q.surname:
                        message = message.replace('<NAME>', q.surname.title())
                #print "%s Message: %s" % (q.phone_number, message)
                sms = sendMemberSMS(self.request, q, message)
                if sms:
                    count += 1
            jres = {'status': 'success', 'message': '%s Messages sent. <div><small>If some messages were not sent, Please check the send Message status of the Cooperative</small</div>' % count}
        except Exception:
            log_error()
            jres = {'status': 'error', 'message': 'Error! Message not sent. Contact Admin.'}
        return JsonResponse(jres)
    
    
class CooperativeMemberDetailView(ExtraContext, DetailView):
    model = CooperativeMember
    
    def get_queryset(self):
        qs = super(CooperativeMemberDetailView, self). get_queryset()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            qs = qs.filter(cooperative=cooperative) 
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(CooperativeMemberDetailView, self).get_context_data(**kwargs)
        context['training'] = TrainingAttendance.objects.filter(coop_member__id=self.kwargs.get('pk'))
        context['seasons'] = Season.objects.all()
        print(self.kwargs.get('pk'))
        member = CooperativeMember.objects.get(pk=self.kwargs.get('pk'))
        context['oko_location'] = OKOLocation.objects.all()
        if member.district:
            context['oko_location'] = OKOLocation.objects.filter(district=member.district.name)

        #raise Exception(context['training'])
        return context
    

class MemberSubscriptionListView(ExtraContext, ListView):
    model = CooperativeMemberSubscriptionLog
    

class MemberSubscriptionCreateView(ExtraContext, CreateView):
    model = CooperativeMemberSubscriptionLog
    form_class = MemberSubscriptionForm
    success_url = reverse_lazy('coop:member_subscription_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.transaction_id = generate_alpanumeric()
        bal_before = form.instance.cooperative_member.subscription_amount
        bal_after = bal_before + form.instance.amount_paid
        form.instance.cooperative_member.subscription_amount = bal_after
        form.instance.cooperative_member.save()
        # form.instance.new_balance = bal_after
        return super(MemberSubscriptionCreateView, self).form_valid(form)
    
    
class MemberSubscriptionUpdateView(ExtraContext, UpdateView):
    model = CooperativeMemberSubscriptionLog
    form_class = MemberSubscriptionForm
    success_url = reverse_lazy('coop:member_subscription_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeMemberSubscriptionLog.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative_member.subscription_amount
        deducted = acc_bal - cont.amount_paid
        final = deducted + form.instance.amount_paid
        form.instance.cooperative_member.subscription_amount = final
        form.instance.cooperative_member.save()
        # form.instance.new_balance = final
        return super(MemberSubscriptionUpdateView, self).form_valid(form)


class MemberSharesView(ListView):
    model = CooperativeMemberSharesLog
    template_name = 'coop/MemberShares.html'
    
    def get_queryset(self):
        queryset = CooperativeMemberSharesLog.objects
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(cooperative_member__cooperative = cooperative)
        queryset = queryset.values('cooperative_member',
                                   name=Concat('cooperative_member__surname',
                                               V(' '),
                                               'cooperative_member__first_name'
                                               ),
                                   
                                   ).annotate(total_amount=Sum('amount'), total_shares=Sum('shares'), transaction_date=Max('transaction_date')).order_by('-transaction_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberSharesView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member_shares']
        return context


# Registrton
class MemberRegistrationTransactionListView(ExtraContext, ListView):
    model = RegistrationTransaction
    template_name = 'coop/memberregistrationlist.html'

    def get_queryset(self):
        queryset = RegistrationTransaction.objects.all()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            queryset = queryset.filter(member__cooperative=cooperative)
        member = self.kwargs.get('member')
        if member:
            queryset = queryset.filter(member=member)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(MemberRegistrationTransactionListView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_reg_shares']
        return context


class MemberRegistrationTransactionCreateView(FormView):
    # model = RegistrationTransaction
    form_class = RegistrationTransactionForm
    success_url = reverse_lazy('coop:registration_list')
    template_name = "coop/registrationtransaction_form.html"

    def get_form_kwargs(self, **kwargs):
        kwargs = super(MemberRegistrationTransactionCreateView, self).get_form_kwargs(**kwargs)
        kwargs['request'] = self.request  # pass the 'user' in kwargs
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        transaction_id = generate_alpanumeric()
        msisdn = form.cleaned_data.get('phone_number')
        member = form.cleaned_data.get('member')
        amount = form.cleaned_data.get('amount')

        registration = RegistrationTransaction.objects.filter(member=member)
        if registration.exists():
            return JsonResponse({"error": True, "response": "This member is arleady registered."})

        try:
            msisdn = internationalize_number(msisdn)
        except Exceptoin as e:
            return JsonResponse({"error": True, "response": "Phone Number provided is invalid."})

        account = member.cooperative.account

        try:
            transaction = AccountTransaction.objects.create(
                account=account,
                reference = genetate_uuid4(),
                amount = amount,
                phone_number = msisdn,
                transaction_type = 'COLLECTION',
                entry_type = 'CREDIT',
                category = 'REGISTRATION',
                status = 'PENDING',
                description = 'REGISTRATION FEE for %s' % member,
                request = '',
                request_date = datetime.now(),
                created_by = self.request.user
            )

            credentials = {
                'password': 'W3E4g8weR5TgH0Td2344',
                'accountid': 'andrew',
                'http_credentials': 'andrew:hamwe'
            }
            hamwepay = HamwePay(credentials)

            payload = {
                "reference": transaction.reference,
                "method": 'COLLECTION',
                "amount": "%s" % transaction.amount,
                "phone_number": transaction.phone_number,
            }
            response = hamwepay.mobile_money_transaction(payload)
            status_checking = None
            if response:
                transaction.response = response
                transaction.response_date = datetime.now()
                transaction.save()
                if response.get("transactionStatus") == 'PENDING':
                    status_checking = response
                    reference = response.get('transactionReference')
                    loop = 1
                    while loop == 1:
                        time.sleep(2)
                        log_debug("Check Status")
                        status_checking = hamwepay.check_status(reference)
                        if not status_checking:
                            loop = 0
                        if status_checking.get('status') == 'ERROR':
                            loop = 0
                        if status_checking.get('status') == 'OK':
                            if status_checking.get('statusMessage') != "PENDING":
                                loop = 0
                        else:
                            loop = 0
                log_debug("End Check Status %s" % status_checking)
                if status_checking.get('statusMessage') != "PENDING":
                    transaction.response = status_checking
                    transaction.status = status_checking.get('statusMessage')
                    transaction.response_date = datetime.now()
                    transaction.payment_date = datetime.now()

                    if status_checking.get('statusMessage') == "SUCCESSFUL":

                        balance = account.balance
                        new_balance = balance + amount
                        account.balance = new_balance
                        account.save()

                        transaction.balance_after = new_balance

                        RegistrationTransaction.objects.create(
                            transaction_id=transaction.reference,
                            member = member,
                            amount = transaction.amount,
                            payment_date = datetime.now()
                        )
                        return JsonResponse({"error": False, "response": "Transaction Successful"})
                    elif status_checking.get('statusMessage') == "FAILED":
                        return JsonResponse({"error": True, "response": "Transaction Failed Failed"})
                    else:
                        return JsonResponse({"error": True, "response": "Unknown Status. Contact Admin"})
                transaction.save()

            print(response)

            # try:
            #     message = message_template().member_share_purchase
            #     message = message.replace('<NAME>', member.surname)
            #     message = message.replace('<SHARES>', '%s' % form.instance.shares)
            #     message = message.replace('<AMOUNT>', '%s' % form.instance.amount)
            #     message = message.replace('<TOTAL>', '%s' % bal_after)
            #     message = message.replace('<REFERENCE>', form.instance.transaction_id)
            #     sendMemberSMS(self.request, member, message)
            # except Exception:
            #     log_error()
            # return super(MemberRegistrationTransactionCreateView, self).form_valid(form)
        except Exception as e:
            log_error()
            return JsonResponse({"error": True, "response": "Transaction Failed. Contact Admin"})
        return JsonResponse({"error": False, "response": "Error"})


class MemberSharesUpdateView(UpdateView):
    model = CooperativeMemberSharesLog
    form_class = MemberSharesForm
    success_url = reverse_lazy('coop:member_shares_list')

    def get_form_kwargs(self):
        kwargs = super(MemberSharesUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request  # pass the 'user' in kwargs
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeMemberSharesLog.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative_member.shares
        deducted = acc_bal - cont.shares
        final = deducted + form.instance.shares
        form.instance.cooperative_member.shares = final
        form.instance.cooperative_member.save()
        form.instance.new_shares = final
        return super(MemberSharesUpdateView, self).form_valid(form)
# /Registration

class MemberSharesListView(ExtraContext, ListView):
    model = CooperativeMemberSharesLog
    template_name = 'coop/cooperativemembersharelog_list.html'
    
    def get_queryset(self):
        queryset = CooperativeMemberSharesLog.objects.all()
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative 
            queryset = queryset.filter(cooperative_member__cooperative=cooperative)
        member = self.kwargs.get('member')
        if member:
            queryset = queryset.filter(cooperative_member=member)
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super(MemberSharesListView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_member_shares']
        return context
    

class MemberSharesCreateView(CreateView):
    model = CooperativeMemberSharesLog
    form_class = MemberSharesForm
    success_url = reverse_lazy('coop:member_shares_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberSharesCreateView, self).get_form_kwargs()
        kwargs['request'] = self.request # pass the 'user' in kwargs
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.transaction_id = generate_alpanumeric()
        bal_before = form.instance.cooperative_member.shares
        amt_before = form.instance.cooperative_member.share_amount
        bal_after = bal_before + form.instance.shares
        amt_after = amt_before + form.instance.amount
        form.instance.cooperative_member.shares = bal_after
        form.instance.cooperative_member.share_amount = amt_after
        form.instance.cooperative_member.save()
        form.instance.new_shares = bal_after
        member = form.instance.cooperative_member
        try:
            message = message_template().member_share_purchase
            message = message.replace('<NAME>', member.surname)
            message = message.replace('<SHARES>', '%s' % form.instance.shares)
            message = message.replace('<AMOUNT>', '%s' % form.instance.amount)
            message = message.replace('<TOTAL>', '%s' %  bal_after)
            message = message.replace('<REFERENCE>', form.instance.transaction_id)
            sendMemberSMS(self.request, member, message)
        except Exception:
            log_error()
        return super(MemberSharesCreateView, self).form_valid(form)
    
    
class MemberSharesUpdateView(UpdateView):
    model = CooperativeMemberSharesLog
    form_class = MemberSharesForm
    success_url = reverse_lazy('coop:member_shares_list')
    
    def get_form_kwargs(self):
        kwargs = super(MemberSharesUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request # pass the 'user' in kwargs
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        cont = CooperativeMemberSharesLog.objects.get(pk=form.instance.id)
        acc_bal = form.instance.cooperative_member.shares
        deducted = acc_bal - cont.shares
        final = deducted + form.instance.shares
        form.instance.cooperative_member.shares = final
        form.instance.cooperative_member.save()
        form.instance.new_shares = final
        return super(MemberSharesUpdateView, self).form_valid(form)
    

class MemberSupplyRequestListView(ListView):
    model = MemberSupplyRequest
    ordering = ['-create_date']
    
    def get_queryset(self):
        queryset = super(MemberSupplyRequestListView, self).get_queryset()
        
        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative 
                queryset = queryset.filter(cooperative_member__cooperative=cooperative)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberSupplyRequestListView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        return context
    
    
class MemberSupplyRequestCreateView(View):
    
    template_name = 'coop/membersupplyrequest_form.html'
    
    def get(self, request, *args, **kwargs):
        initial = None
        supply = None
        extra = 1
        pk = self.kwargs.get('pk')
        if pk:
            supply = MemberSupplyRequest.objects.get(pk=pk)
            pvars = MemberSupplyRequestVariation.objects.filter(supply_request=supply)
            initial = [{'breed': x.breed, 'total': x.total} for x in pvars]
            extra = 0 if len(initial) > 0 else 1
        
        form = MemberSupplyRequestForm(instance=supply, request=request)
        
        variation_formset = formset_factory(MemberSupplyRequestVariationForm, formset=VariationSupplyRequestFormSet, extra=extra)
        variation_form = variation_formset(prefix='variation', initial=initial)
        return render(request, self.template_name, {'form': form, 'variation_form': variation_form, 'active': ['_coop_supply_request', '']})
    
    def post(self, request, *args, **kwargs):
        initial = None
        supply = None
        extra = 1
        pk = self.kwargs.get('pk')
        if pk:
            supply = MemberSupplyRequest.objects.get(pk=pk)
            pvars = MemberSupplyRequestVariation.objects.filter(supply_request=supply)
            initial = [{'breed': x.breed, 'total': x.total} for x in pvars]
            extra = 0 if len(initial) > 0 else 1
        form = MemberSupplyRequestForm(request.POST, request=request, instance=supply)
        variation_formset = formset_factory(MemberSupplyRequestVariationForm, formset=VariationSupplyRequestFormSet, extra=extra)
        variation_form = variation_formset(request.POST, prefix='variation', initial=initial)
        if form.is_valid() and variation_form.is_valid():
            try:
                with transaction.atomic():
                    
                    req = form.save(commit=False)
                    if not pk:
                        req.transaction_reference = generate_alpanumeric(prefix="SR", size=8)
                    req.created_by = request.user
                    req.save()
                    if pk:
                        MemberSupplyRequestVariation.objects.filter(supply_request=req).delete()
                    for c in variation_form:
                        if len(c.cleaned_data) > 0:
                            cf = c.save(commit=False)
                            cf.supply_request = req
                            cf.created_by = request.user
                            cf.save()
                    
                    try:
                        message = message_template().supply_request
                        message = message.replace('<NAME>', req.cooperative_member.surname)
                        message = message.replace('<NUMBER>', '%s' % req.get_sum_total())
                        message = message.replace('<DATE>', '%s' % req.supply_date)
                        message = message.replace('<REFERENCE>', req.transaction_reference)
                        sendMemberSMS(self.request, req.cooperative_member, message)
                    except Exception:
                        log_error()
                    return redirect('coop:request_list')
                    
            except Exception as e:
                form.add_error(None, "Supply Request Error! Contact Admin")
                log_error()
        return render(request, self.template_name, {'form': form, 'variation_form': variation_form, 'active': ['_coop_supply_request', '']})
      
    
class MemberSupplyRequestDetailView(FormMixin, DetailView):
    model = MemberSupplyRequest
    form_class = MemberSupplyRequestConfirmForm
    
    def get_success_url(self):
        return reverse('coop:request_list')
    
    def get_context_data(self, **kwargs):
        context = super(MemberSupplyRequestDetailView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        instance = MemberSupplyRequest.objects.get(pk=self.kwargs.get('pk'))
        context['form'] = MemberSupplyRequestConfirmForm(instance = instance)
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        instance = MemberSupplyRequest.objects.get(pk=self.kwargs.get('pk'))
        form = MemberSupplyRequestConfirmForm(request.POST, instance = instance)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        # Here, we would record the user's interest using the message
        # passed in form.cleaned_data['message']
        form.instance.confirmation_logged_by = self.request.user
        form.save()
        
        try:
            message = message_template().supply_confirmation
            if form.instance.status == 'ACCEPTED':
                message = message.replace('<NAME>', form.instance.cooperative_member.surname)
                message = message.replace('<DATE>', '%s' % form.instance.supply_date)
                message = message.replace('<REFERENCE>', form.instance.transaction_reference)
                
            else:
                message = message_template().supply_cancelled
                message = message.replace('<NAME>', form.instance.cooperative_member.surname)
                message = message.replace('<REFERENCE>', form.instance.transaction_reference)
            sendMemberSMS(self.request, form.instance.cooperative_member, message)
        except Exception:
            log_error()
        messages.success(self.request, 'Request %s Confirmed' % form.instance.transaction_reference)
        return super(MemberSupplyRequestDetailView, self).form_valid(form)


class SupplyConfirmationView(UpdateView):
    model = MemberSupplyRequest
    form_class = MemberSupplyRequestConfirmForm
    
    def get_context_data(self, **kwargs):
        context = super(SupplyConfirmationView, self).get_context_data(**kwargs)
        context['active'] = ['_coop_supply_request', '']
        return context


class MembersMapView(TemplateView):
    template_name = "coop/farmer_map.html"

    def get_context_data(self, **kwargs):
        context = super(MembersMapView, self).get_context_data(**kwargs)
        context['form'] = MemberProfileSearchForm(self.request.GET, request=self.request)
        return context


def get_farmer_map(request):
    farmer = CooperativeMember.objects.all()
    data = []
    for f in farmer:
        if f.gps_coodinates:
            data.append({"name": f.get_name(), "gps": f.gps_coodinates})
    print(data)
    return JsonResponse(data, safe=False)


class OKOListView(ListView):
    model = OKOMemberPolicy


class OKOCreatePolicyView(View):

    def get(self, request, **kwargs):
        member = CooperativeMember.objects.get(pk=self.kwargs.get('pk'))
        season_id = self.request.GET.get('season_id')
        sub_county = self.request.GET.get('sub_county')
        district = OKOLocation.objects.get(sub_county=sub_county)

        payload = {
            "district": {
                "name": district.district
            },
            "county": "",
            "sub_county": sub_county ,
            "member_id": member.member_id,
            "surname": member.surname,
            "first_name": member.first_name,
            "other_name": member.other_name if member.other_name else "",
            "gender": member.gender,
            "date_of_birth": member.date_of_birth.strftime('%Y-%m-%d') if member.date_of_birth else "",
            "phone_number": member.phone_number.replace("256", "") if member.phone_number else "",
            "land_acreage": str(member.land_acreage) if member.land_acreage else "",
            "seasonId":season_id
        }

        print(payload)
        try:
            if member.land_acreage:
                oko = OKOTransaction()
                res = oko.CreatePolicyPartner(payload)

                if "policyId" in res and res.get('policyId'):
                    policyId = res.get('policyId')
                    amountDue = res.get('amountDue')

                    try:
                        season = Season.objects.get(session_id=season_id)
                    except Exception as e:
                        season = None

                    qs = OKOMemberPolicy.objects.filter(policyId=policyId)
                    if qs.exists():
                        qs = qs[0]
                        qs.amount_due = amountDue
                        if season:
                            qs.season = season
                        qs.save()
                    else:
                        OKOMemberPolicy.objects.create(
                            cooperative_member=member,
                            season=season,
                            policyId = policyId,
                            amount_due = amountDue,
                            created_by = request.user
                        )
                    messages.success(self.request, "Policy created.")
                else:
                    messages.error(self.request, "Policy creation failed.")
            else:
                messages.error(self.request, "Please provide the Agents Land Acreage")
        except Exception as e:
            log_error()
            messages.error(self.request, "Policy creation failed.")

        return redirect('coop:member_detail', pk=member.id)


class OKOCheckPolicyView(View):

    def get(self, request, **kwargs):
        from django.utils.dateparse import parse_datetime
        pk = self.kwargs.get('pk')
        okop = OKOMemberPolicy.objects.get(pk=pk)
        # {u'totalPaid': 0.0, u'endDate': u'2022-09-21T00:00:00', u'amountLeft': 123000.0, u'claimStatus': 1}
        try:
            oko = OKOTransaction()
            res = oko.ChecckPolicy(okop.policyId)
            okop.amount_paid = res.get('totalPaid')
            okop.amount_due = res.get('amountLeft')
            okop.claim_status = res.get('claimStatus')
            datetime_object = parse_datetime(res.get('endDate'))
            okop.end_date = datetime_object
            okop.save()
            return redirect('coop:member_detail', pk=okop.cooperative_member.id)
        except Exception as e:
            log_error()
            messages.error(self.request, "Policy Check failed.")
            return redirect('coop:member_detail', pk=okop.cooperative_member.id)


class OKOLocationUploadView(View):

    template_name = 'coop/collection_upload.html'

    def get(self, reqeust, *args, **kwargs):
        data = {}
        data['form'] = OKOLocationForm
        return render(reqeust, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = OKOLocationForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1

            region_col = 0
            district_col = 1
            sub_county_col = 2

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            location_list = []
            member = None

            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i + 1

                    region = smart_str(row[region_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-]+$', region, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Region (row %d)' % \
                                         (region, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    district = smart_str(row[district_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-]+$', district, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid District (row %d)' % \
                                         (district, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})
                    sub_county = smart_str(row[sub_county_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\/\.]+$', sub_county, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Sub County (row %d)' % \
                                         (sub_county, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})


                    location_list.append({
                        "region": region,
                        "district":district,
                        "sub_county": sub_county
                    })

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})

            print(location_list)
            if location_list:
                try:
                    for l in location_list:
                        obj, create = OKOLocation.objects.get_or_create(
                            region = l['region'],
                            district = l['district'],
                            sub_county = l['sub_county'],
                        )

                    return redirect('coop:oko_location_list')
                except Exception as e:
                    log_error()
                    return render(request, self.template_name,
                                  {'active': 'setting', 'form': form, 'error': e})


class OKOLocationListView(ListView):
    model = OKOLocation
