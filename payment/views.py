# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import re
import xlwt
import xlrd
import json
from django.utils.encoding import smart_str
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, HttpResponse
from django.db import transaction
from django.db.models import Q
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from payment.forms import MemberPaymentForm, BulkPaymentForm, PaymentFilterForm
from payment.models import MemberPayment, MemberPaymentTransaction, BulkPaymentRequest, BulkPaymentRequestLog
from payment.utils import payment_transction
from coop.AccountTransactions import AccountTransaction
from payment.PaymentTransaction import PaymentTransaction
from coop.models import Cooperative, CooperativeMember

from conf.utils import generate_alpanumeric, log_debug, log_error

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_payment']
        context.update(self.extra_context)
        return context
    

class PaymentMethodListView(ExtraContext, ListView):
    model = MemberPaymentTransaction
    ordering = ['-payment_date']
    extra_context = {'active': ['_payment']}
    
    def get_queryset(self):
        queryset = super(PaymentMethodListView, self).get_queryset()
        
        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative 
                queryset = queryset.filter(Q(member__cooperative=cooperative)| Q(cooperative=cooperative))
        
        search = self.request.GET.get('search')
        cooperative = self.request.GET.get('cooperative')
        status = self.request.GET.get('status')
        payment_method = self.request.GET.get('payment_method')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if search:
            queryset = queryset.filter(Q(transaction_reference__icontains=search)|Q(member__first_name__icontains=search)|Q(member__surname__icontains=search)|Q(member__phone_number__icontains=search)|Q(member__member_id__icontains=search))
        if cooperative:
            queryset = queryset.filter(cooperative__id = cooperative)
        if status:
            queryset = queryset.filter(status = status)
        if payment_method:
            queryset = queryset.filter(payment_method = payment_method)
        if start_date and end_date:
            queryset = queryset.filter(payment_date__gte = start_date, payment_date__lte = end_date)
        if start_date:
            queryset = queryset.filter(payment_date = start_date)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(PaymentMethodListView,self).get_context_data(**kwargs)
        context['form'] = PaymentFilterForm(self.request.GET)
        return context
        

class PaymentTransactionDetail(ExtraContext, DetailView):
    model = MemberPaymentTransaction
   
    
class PaymentMethodCreateView_deprec(ExtraContext, CreateView):
    model = MemberPayment
    form_class = MemberPaymentForm
    extra_context = {'active': ['_payment']}
    success_url = reverse_lazy('payment:list')
    
    def form_valid(self, form):
        reference = generate_alpanumeric()
        form.instance.user = self.request.user
        form.instance.transaction_id = reference
        form.instance.payment_reference = generate_alpanumeric("HP-", 10)
        msisdn = form.instance.member.phone_number
        amount = form.instance.amount
        form.instance.status = 'SUCCESSFUL'
        if form.instance.payment_method == 'MOBILE MONEY':
            res = payment_transction(msisdn, amount, reference)
            form.instance.status = res['status']
            form.instance.response = res
            form.instance.response_date = datetime.datetime.now()
        trx = form.save()
        
        if form.instance.status == 'SUCCESSFUL':
            #update payment transaction
            bal_before = form.instance.member.paid_amount
            bal_after = amount + bal_before
            
            MemberPaymentTransaction.objects.create(
                request_id = trx,
                member = trx.member,
                transaction_reference = generate_alpanumeric("PMT", 8),
                balance_before = bal_before,
                amount = amount,
                balance_after = bal_after
            )
            
            # update user account
            at = AccountTransaction(trx.member)
            at._update_payment(bal_after)
        
        return super(PaymentMethodCreateView, self).form_valid(form)


class PaymentTransactionCreateView(ExtraContext, CreateView):
    model = MemberPaymentTransaction
    form_class = MemberPaymentForm
    extra_context = {'active': ['_payment']}
    success_url = reverse_lazy('payment:list')
    
    def form_valid(self, form):
        form.instance.transaction_reference = generate_alpanumeric('60', 10)
        form.instance.creator = self.request.user
        msisdn = form.instance.member.phone_number
        amount = form.instance.amount
        form.instance.status = 'PENDING'
        trx = form.save()
        
        pt = PaymentTransaction(form.instance.member, self.request)
        pt.transaction_request(payment_request=trx)
        # if form.instance.payment_method == 'MOBILE MONEY':
        #     # make MM Request
        #     res = payment_transction(msisdn, amount, reference)
        #     form.instance.status = res['status']
        # trx = form.save()
        
        # if form.instance.status == 'SUCCESSFUL':
        #     #update payment transaction
        #     bal_before = form.instance.member.paid_amount
        #     bal_after = amount + bal_before
        #     
        #     form.instance.balance_before
        #     form.instance.balance_after
        #     form.instance.balance_after
        #     
        #     # MemberPaymentTransaction.objects.create(
        #     #     request_id = trx,
        #     #     member = trx.member,
        #     #     transaction_reference = generate_alpanumeric("PMT", 8),
        #     #     balance_before = bal_before,
        #     #     amount = amount,
        #     #     balance_after = bal_after
        #     # )
        #     
        #     # update user account
        #     at = AccountTransaction(trx.member)
        #     at._update_payment(bal_after)
        
        return super(PaymentTransactionCreateView, self).form_valid(form)


class BulkPaymentView(View):
    template_name = 'payment/paymentupload_form.html'
    
    def get(self, request, *args, **kwargs):
        form = BulkPaymentForm
        data ={
            'form': form
            }
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs):
        data = dict()
        form = BulkPaymentForm(request.POST, request.FILES)
        payment_method = None
        cooperative = None
        
        if form.is_valid():
            
            cooperative = form.cleaned_data['cooperative']
            payment_method = form.cleaned_data['payment_method']
            excel_file = form.cleaned_data['excel_file']
            
            f = request.FILES['excel_file']
            
            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet'])-1
            startrow = int(form.cleaned_data['row'])-1
            
            phone_number_col = int(form.cleaned_data['phone_number_col'])
            amount_col = int(form.cleaned_data['amount_col'])
            transaction_date_col = int(form.cleaned_data['transaction_date_col'])
            
            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            payment_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i+1
                    try:
                        phone_number = int(row[phone_number_col].value)
                    except Exception:
                        data['errors'] = '"%s" is not a valid Phone number (row %d)' % \
                        (phone_number, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    
                        
                    # if not re.search('^[0-9]+$', phone_number, re.IGNORECASE):
                    #     if (i+1) == sheet.nrows: break
                    #     data['errors'] = '"%s" is not a valid Phone number (row %d)' % \
                    #     (phone_number, i+1)
                    #     return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    # 
                    amount = smart_str(row[amount_col].value).strip()
                    if not re.search('^[0-9\.]+$', amount, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Amount Figure (row %d)' % \
                        (amount, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    transaction_date = None
                    if len(row) == 3:
                        transaction_date = (row[transaction_date_col].value)
                        if transaction_date:
                            try:
                                date_str = datetime(*xlrd.xldate_as_tuple(int(transaction_date), book.datemode))
                                transaction_date = date_str.strftime("%Y-%m-%d")
                            except Exception as e:
                                data['errors'] = '"%s" is not a valid Transaction Date (row %d)' % \
                                (e, i+1)
                                return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                       
                        
                    # phone_number = (row[phone_number_col].value)
                    # if phone_number:
                    #     try:
                    #         phone_number = int(phone_number)
                    #     except Exception as e:
                    #         print e
                    #     if not re.search('^[0-9]+$', str(phone_number), re.IGNORECASE):
                    #         data['errors'] = '"%s" is not a valid Phone Number (row %d)' % \
                    #         (phone_number, i+1)
                    #         return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
                    # 
                    
                   
                    try:
                        member = CooperativeMember.objects.get(phone_number=phone_number, cooperative__id=cooperative)
                    except Exception as e:
                        log_error()
                        data['errors'] = 'Member with phone number "%s" Not found (row %d) in the selected cooperative' % \
                        (phone_number, i+1)
                        return render(request, self.template_name, {'active': 'system', 'form':form, 'error': data})
        
                    q = {'member': member ,
                         'amount': amount,
                         'transaction_date': transaction_date,
                         'cooperative': cooperative,
                        }
                    payment_list.append(q)
                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})
             
            if payment_list:
                with transaction.atomic():
                    try:
                        total_amount = 0
                        cooperative = Cooperative.objects.get(pk=cooperative)
                        bulk_request = BulkPaymentRequest.objects.create(
                            file_name = excel_file,
                            cooperative = cooperative,
                            total_amount = total_amount,
                            payment_method = payment_method,
                            status = 'PENDING',
                            created_by = request.user
                        )
                        for c in payment_list:
                            
                            cooperative = c.get('cooperative')
                            member = c.get('member')
                            amount = c.get('amount')
                            transaction_date = c.get('transaction_date') if c.get('transaction_date') else datetime.datetime.now().strftime("%Y-%m-%d")

                            bulk_plog = BulkPaymentRequestLog.objects.create(
                                bulk_payment_request = bulk_request,
                                member = member,
                                amount = amount,
                                payment_method = payment_method,
                                transaction_date = transaction_date,
                                process_state = 'PENDING',
                                created_by = request.user
                            )
                            total_amount += float(amount)
                        bulk_request.total_amount = total_amount
                        bulk_request.save()
                        return redirect('payment:bulk_detail', pk=bulk_request.id)
                    except Exception as err:
                        log_error()
                        data['error'] = err
                
        data['form'] = form
        return render(request, self.template_name, data)
    
    
class BulkPaymentListView(ExtraContext, ListView):
    model = BulkPaymentRequest
    ordering = ['-update_date']
    

class BulkPaymentDetail(ExtraContext, DetailView):
    model = BulkPaymentRequest


class BulkPaymentConfirm(ExtraContext, View):
    def post(self, request, *arg, **kwarg):
        payment_method = request.POST.get('payment_method')
        pk = self.kwargs.get('pk')
        try:
            res = {"status": "error", "message": "Transaction Duplicate"}
            req = BulkPaymentRequest.objects.filter(pk=pk).exclude(status='COMPLETED')
            if req.exists():
                req = req[0]
                req.status = 'PROCESSING'
                req.save()
                bulk_logs = BulkPaymentRequestLog.objects.filter(bulk_payment_request=req)
                for r in bulk_logs:
                    params = {
                        'cooperative': req.cooperative,
                        'amount': r.amount,
                        'payment_date': r.transaction_date,
                        'payment_method': payment_method,
                        'user': request.user,
                        'status': 'PENDING'
                    }
                    r.process_state = 'COMPLETED'
                    r.save()
                    pt = PaymentTransaction(r.member, request)
                    pt.transaction_request(params=params)
                req.status = 'COMPLETED'
                req.save()
                res = {"status": "success", "message": "Transaction Successfull"}
        except Exception:
            log_error()
            req.status = 'FAILED'
            res = {"status": "success", "message": "Transaction Failed"}

        return HttpResponse(json.dumps(res), status=200)


class BulkPaymentDelete(ExtraContext, View):
    def post(self, request, *arg, **kwarg):
        try:
            pk = self.kwargs.get('pk')
            BulkPaymentRequest.objects.filter(pk=pk).delete()
            res = {"status": "success", "message": "Transaction Deleted!"}
        except Exception:
            log_error()
            res  = {"status": "success", "message": "Delete Failed!"}
        return HttpResponse(json.dumps(res), status=200)
            

class PaymentMethodUpateView(UpdateView):
    model = MemberPayment
    
    
class DownloadPaymentExcelView(View):
    
    def get(self, request, *args, **kwargs):
        _choices = ['id','payment_date', 'cooperative__name', 'member__member_id', 'amount', 'payment_method', 'transaction_reference', 'status']
        columns = []
        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in _choices]
        
        #Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that 
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')
        
        # The response also has additional Content-Disposition header, which contains 
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=MembersPayment_%s.xls' % datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
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
        
       
        _payment = MemberPaymentTransaction.objects.values(*_choices).all()
        search = self.request.GET.get('search')
        cooperative = self.request.GET.get('cooperative')
        status = self.request.GET.get('status')
        payment_method = self.request.GET.get('payment_method')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if search:
            _payment = _payment.filter(Q(transaction_reference__icontains=search)|Q(member__first_name__icontains=search)|Q(member__surname__icontains=search)|Q(member__phone_number__icontains=search)|Q(member__member_id__icontains=search))
        if cooperative:
            _payment = _payment.filter(cooperative__id = cooperative)
        if status:
            _payment = _payment.filter(status = status)
        if payment_method:
            _payment = _payment.filter(payment_method = payment_method)
        if start_date and end_date:
            _payment = _payment.filter(payment_date__gte = start_date, payment_date__lte = end_date)
        if start_date:
            _payment = _payment.filter(payment_date = start_date)
        
        
        for m in _payment:
            row_num += 1
            row = [ m['%s' % x ] if not 'payment_date' in x else m['%s' % x ].strftime("%Y-%m-%d") for x in _choices]
            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response
    
    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces :
            # Check if string is in the main string
            if elem in mainString :
                # Replace the string
                mainString = mainString.replace(elem, newString)
        
        return  mainString
