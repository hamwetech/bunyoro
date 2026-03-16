# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import magic
import re
import xlrd
import xlwt
from datetime import datetime
from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse_lazy
from django.utils.encoding import smart_str
from django.db.models import Q
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from coop.models import Collection, CooperativeMember
from coop.forms import CollectionForm, CollectionFilterForm, CollectionUploadForm
from coop.views.member import save_transaction
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, get_message_template as message_template
from coop.utils import sendMemberSMS

from product.models import ProductVariation, ProductVariationPrice


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_collection']
        context.update(self.extra_context)
        return context

class CollectionListView(ExtraContext, ListView):
    model = Collection
    ordering = ['-create_date']
    extra_context = {'active': ['_collection']}
    
    def dispatch(self, request, *args, **kwargs):
        if self.request.GET.get('_download'):
            return redirect('coop:collection_download')
        else:
            return super(CollectionListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super(CollectionListView, self).get_queryset()
        
        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative 
                queryset = queryset.filter(Q(member__cooperative=cooperative)| Q(cooperative=cooperative))
        search = self.request.GET.get('search')
        product = self.request.GET.get('product')
        cooperative = self.request.GET.get('cooperative')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if search:
            queryset = queryset.filter(Q(member__first_name__icontains=search)|Q(member__surname__icontains=search)|Q(member__phone_number__icontains=search)|Q(member__member_id__icontains=search))
        if product:
            queryset = queryset.filter(product__id = product)
        if cooperative:
            queryset = queryset.filter(cooperative__id = cooperative)
        if start_date and end_date:
            queryset = queryset.filter(collection_date__gte = start_date, collection_date__lte = end_date)
        if start_date:
            queryset = queryset.filter(collection_date = start_date)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(CollectionListView, self).get_context_data(**kwargs)
        context['form'] = CollectionFilterForm(self.request.GET)
        return context


class CollectionDownload(View):
    def get(self, request, *args, **kwargs):
        columns = []
        fields = ['id', 'is_member', 'cooperative__name', 'member__surname', 'member__first_name', 'member__phone_number', 'collection_reference', 'product__name', 'quantity',
                               'unit_price', 'total_price', 'created_by']
        columns = [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in fields]
        
        #Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that 
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')
        
        # The response also has additional Content-Disposition header, which contains 
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=CollectionLogs_%s.xls' % datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create object for the Workbook which is under xlwt library.
        workbook = xlwt.Workbook()
        
        # By using Workbook object, add the sheet with the name of your choice.
        worksheet = workbook.add_sheet("Collections")

        row_num = 0
        style_string = "font: bold on; borders: bottom dashed"
        style = xlwt.easyxf(style_string)

        for col_num in range(len(columns)):
            # For each cell in your Excel Sheet, call write function by passing row number, 
            # column number and cell data.
            worksheet.write(row_num, col_num, columns[col_num], style=style)
        
        _collection = Collection.objects.values(*fields).all()
        for m in _collection:
            row_num += 1
            row = [m['%s' % x] for x in fields]
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
         

    
class CollectionCreateView(ExtraContext, CreateView):
    model = Collection
    extra_context = {'active': ['_collection']}
    form_class = CollectionForm
    success_url = reverse_lazy('coop:collection_list')
    
    def get_form_kwargs(self):
        kwargs = super(CollectionCreateView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs
    
    def form_valid(self, form):
        form.instance.collection_reference = genetate_uuid4()
        form.instance.created_by = self.request.user
        #form.instance.cooperative = self.request.user.cooperative_admin.cooperative
        
        if form.instance.is_member:
            params = {'amount': form.instance.total_price,
                      'member': form.instance.member,
                      'transaction_reference': form.instance.collection_reference ,
                      'transaction_type': 'COLLECTION',
                      'entry_type': 'CREDIT'
                      }
            member = CooperativeMember.objects.filter(pk=form.instance.member.id)
            if member.exists():
                member = member[0]
                qty_bal = member.collection_quantity if member.collection_quantity else 0
                
                new_bal = form.instance.quantity + qty_bal
                member.collection_quantity = new_bal
                member.save()
            save_transaction(params)
            
            try:
                message = message_template().collection
                message = message.replace('<NAME>', member.surname)
                message = message.replace('<QTY>', "%s%s" % (form.instance.quantity, form.instance.product.unit.code))
                message = message.replace('<PRODUCT>', "%s" % (form.instance.product.name))
                message = message.replace('<COOP>', form.instance.cooperative.name)
                message = message.replace('<DATE>', form.instance.collection_date.strftime('%Y-%m-%d'))
                message = message.replace('<AMOUNT>', "%s" % form.instance.total_price)
                message = message.replace('<REFNO>', form.instance.collection_reference)
                sendMemberSMS(self.request, member, message)
            except Exception:
                log_error()
        member = super(CollectionCreateView, self).form_valid(form)
        return member
      
    
class CollectionUpdateView(UpdateView):
    model = Collection
    form_class = CollectionForm
    extra_context = {'active': ['_collection', '__createcc']}
    success_url = reverse_lazy('activity:collection_create')
    
    def form_valid(self, form):
        form.instance.collection_reference = genetate_uuid4()
        return super(CollectionUpdateView, self).form_valid(form)


class CollectionUploadView(View):

    template_name = 'coop/collection_upload.html'

    def get(self, reqeust, *args, **kwargs):
        data = {}
        data['form'] = CollectionUploadForm
        return render(reqeust, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = CollectionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1

            farmer_reference_col = int(form.cleaned_data['farmer_reference_col'])
            farmer_name_col = int(form.cleaned_data['farmer_name_col'])
            product_col = int(form.cleaned_data['product_col'])
            quantity_col = int(form.cleaned_data['quantity_col'])
            collection_date_col = int(form.cleaned_data['collection_date_col'])

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            order_list = []
            member = None

            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i + 1

                    farmer_reference = smart_str(row[farmer_reference_col].value).strip()
                    farmer_name = smart_str(row[farmer_name_col].value).strip()

                    if farmer_reference:
                        member = CooperativeMember.objects.filter(Q(phone_number=farmer_reference)|Q(member_id=farmer_reference))
                        if member.exists():
                            member = member[0]

                    if not member:
                        if farmer_name:
                            f = farmer_name.split(" ")
                            print(f)
                            last_name = f[0]
                            first_name = f[1]
                            member = CooperativeMember.objects.filter(surname=last_name, first_name=first_name)
                            if member.exists():
                                member = member[0]

                    if not member:
                        data['errors'] = 'Member "%s" not Found, please provide a valid name, phone number or member id. (row %d)' % (farmer_name, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    product = smart_str(row[product_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', product, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Product (row %d)' % \
                                         (item, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    try:
                        pproduct = ProductVariation.objects.get(name=product)
                    except Exception as e:
                        data['errors'] = 'Product %s not found. (row %d)' % (product, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    quantity = smart_str(row[quantity_col].value).strip()
                    if not re.search('^[0-9\.]+$', quantity, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Quantity (row %d)' % \
                                         (quantity, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    collection_date = (row[collection_date_col].value)
                    if collection_date:
                        try:
                            date_str = datetime(*xlrd.xldate_as_tuple(collection_date, book.datemode))
                            collection_date = date_str.strftime("%Y-%m-%d")
                        except Exception as e:
                            data['errors'] = '"%s" is not a valid Order Date (row %d): %s' % \
                                             (collection_date, i + 1, e)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})
                    price = float(pproduct.get_price()) * float(quantity)
                    order_list.append({"member": member, "pproduct":pproduct, "unit_price":float(pproduct.get_price()), "price": price, "quantity": quantity, "collection_date": collection_date})

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})

            print(order_list)
            if order_list:
                try:
                    for order_i in order_list:
                        reference = genetate_uuid4()
                        member = order_i.get("member")
                        pproduct = order_i.get("pproduct")
                        unit_price = order_i.get("unit_price")
                        price = order_i.get("price")
                        quantity = order_i.get("quantity")
                        collection_date = order_i.get("collection_date") if order_i.get("collection_date") else datetime.now()

                        Collection.objects.create(
                            collection_date=collection_date,
                            cooperative=member.cooperative,
                            member=member,
                            collection_reference=reference,
                            product=pproduct,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=price,
                            created_by=self.request.user
                        )

                    return redirect('coop:collection_list')
                except Exception as e:
                    log_error()
                    return render(request, self.template_name,
                                  {'active': 'setting', 'form': form, 'error': e})


