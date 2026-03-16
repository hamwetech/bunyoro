from __future__ import unicode_literals
import os
import magic
import re
import xlrd
import xlwt
import json
import datetime
from django.db import transaction
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse_lazy
from django.db.models import Q, CharField, Max, Value as V
from django.utils.encoding import smart_str
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from coop.models import MemberOrder, OrderItem, CooperativeMember
from coop.forms import OrderItemForm, MemberOrderForm, OrderUploadForm
from coop.views.member import save_transaction

from product.models import Item
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        
        context.update(self.extra_context)
        return context
    
    
class MemberOrderListView(ExtraContext, ListView):
    model = MemberOrder
    ordering = ['-create_date']
    extra_context = {'active': ['_order']}

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(MemberOrderListView, self).dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super(MemberOrderListView, self).get_queryset()
        
        if not self.request.user.profile.is_union():
            if not self.request.user.profile.is_partner():
                cooperative = self.request.user.cooperative_admin.cooperative 
                queryset = queryset.filter(member__cooperative=cooperative)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(MemberOrderListView, self).get_context_data(**kwargs)
        return context

    def download_file(self, *args, **kwargs):

        _value = []
        columns = []
        name = self.request.GET.get('name')
        coop = self.request.GET.get('cooperative')
        create_by = self.request.GET.get('create_by')

        profile_choices = ['order_reference', 'cooperative__name', 'member__surname', 'member__first_name', 'order_price', 'status', 'order_date', 'created_by__username']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        # Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')

        # The response also has additional Content-Disposition header, which contains
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=MemberOrders_%s.xls' % datetime.datetime.now().strftime(
            '%Y%m%d%H%M%S')

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

        _members = MemberOrder.objects.values(*profile_choices).all()


        if name:
            _members = _members.filter(Q(surname__icontains=name) | Q(first_name__icontains=name) | Q(other_name=name))
        if coop:
            _members = _members.filter(cooperative__id=coop)
        if create_by:
            _members = _members.filter(create_by__profile__id=create_by)

        for m in _members:

            row_num += 1
            ##print profile_choices
            row = [
                m['%s' % x] if 'order_date' not in x else m['%s' % x].strftime('%d-%m-%Y') if m.get('%s' % x) else ""
                for x in profile_choices]

            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces:
            # Check if string is in the main string
            if elem in mainString:
                # Replace the string
                mainString = mainString.replace(elem, newString)

        return mainString
    

class MemberOrderCreateView(View):
    template_name = 'coop/order_item_form.html'
    
    def get(self, request, *args, **kwargs):
        
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
       
        form = MemberOrderForm(request=request)
        order_form = formset_factory(OrderItemForm, formset=BaseFormSet, extra=extra)
        order_formset = order_form(prefix='order', initial=initial)
        data = {
            'order_formset': order_formset,
            'form': form,
            'active': ['_order'],
        }
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
        form = MemberOrderForm(request.POST, request=request)
        order_form = formset_factory(OrderItemForm, formset=BaseFormSet, extra=extra)
        order_formset = order_form(request.POST, prefix='order', initial=initial)
        try:
            with transaction.atomic():
                if form.is_valid() and order_formset.is_valid():
                    mo = form.save(commit=False)
                    mo.order_reference = generate_numeric(8, '30')
                    mo.created_by = request.user
                    mo.save()
                    price = 0
                    for orderi in order_formset:
                        os = orderi.save(commit=False)
                        os.order = mo
                        os.unit_price = os.item.price
                        os.created_by = request.user
                        os.save()
                        price += os.price
                    mo.order_price = price
                    mo.save()
                    return redirect('coop:order_list')
        except Exception as e:
            log_error()
        data = {
            'order_formset': order_formset,
            'form': form,
            'active': ['_order'],
        }
        return render(request, self.template_name, data)


class MemberOrderDetailView(ExtraContext, DetailView):
    model = MemberOrder
    extra_context = {'active': ['_order']}


class OrderPayment(View):
    pass
    
    
class MemberOrderDeleteView(ExtraContext, DeleteView):
    model = MemberOrder
    extra_context = {'active': ['_order']}
    success_url = reverse_lazy('coop:order_list')
    
    def get_context_data(self, **kwargs):
        #
        context = super(MemberOrderDeleteView, self).get_context_data(**kwargs)
        #
        
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects']=deletable_objects
        context['model_count']=dict(model_count).items()
        context['protected']=protected
        #
        return context
    

class MemberOrderStatusView(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        status = self.kwargs.get('status')
        today = datetime.datetime.today()
        try:
            mo = MemberOrder.objects.get(pk=pk)
            if status == 'ACCEPT':
                mo.accept_date = today
            if status == 'SHIP':
                mo.ship_date = today
            if status == 'ACCEPT_DELIVERY':
                mo.delivery_accept_date = today
            if status == 'REJECT_DELIVERY':
                mo.delivery_reject_date = today
            if status == 'COLLECTED':
                mo.collect_date = today
            mo.status = status
            mo.save()
        except Exception as e:
            log_error()
        
        return redirect('coop:order_list')


class OrderUploadView(View):

    template_name = 'coop/order_upload.html'

    def get(self, reqeust, *args, **kwargs):
        data = {}
        data['form'] = OrderUploadForm
        return render(reqeust, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = OrderUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1

            farmer_reference_col = int(form.cleaned_data['farmer_reference_col'])
            farmer_name_col = int(form.cleaned_data['farmer_name_col'])
            item_col = int(form.cleaned_data['item_col'])
            quantity_col = int(form.cleaned_data['quantity_col'])
            order_date_col = int(form.cleaned_data['order_date_col'])

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

                    item = smart_str(row[item_col].value).strip()
                    if not re.search('^[A-Z\s\(\)\-\.]+$', item, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Item (row %d)' % \
                                         (item, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    try:
                        pitem = Item.objects.get(name=item)
                    except Exception as e:
                        data['errors'] = 'Item %s not found. (row %d)' % (item, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    quantity = smart_str(row[quantity_col].value).strip()
                    if not re.search('^[0-9\.]+$', quantity, re.IGNORECASE):
                        if (i + 1) == sheet.nrows: break
                        data['errors'] = '"%s" is not a valid Quantity (row %d)' % \
                                         (quantity, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    order_date = (row[order_date_col].value)
                    if order_date:
                        try:
                            date_str = datetime(*xlrd.xldate_as_tuple(order_date, book.datemode))
                            order_date = date_str.strftime("%Y-%m-%d")
                        except Exception as e:
                            data['errors'] = '"%s" is not a valid Order Date (row %d): %s' % \
                                             (order_date, i + 1, e)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})
                    price = float(pitem.price) * float(quantity)
                    order_list.append({"member": member, "item":pitem, "unit_price":float(pitem.price), "price": price, "quantity": quantity, "order_date": order_date})

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})

            print(order_list)
            if order_list:
                try:
                    for order_i in order_list:
                        order_reference = generate_numeric(8, '30')
                        member = order_i.get("member")
                        item = order_i.get("item")
                        unit_price = order_i.get("unit_price")
                        price = order_i.get("price")
                        quantity = order_i.get("quantity")
                        order_date = order_i.get("order_date") if order_i.get("order_date") else datetime.datetime.now()
                        check_order = MemberOrder.objects.filter(status='CREATING', member=member)
                        if check_order.exists():
                            check_order=check_order[0]
                            OrderItem.objects.create(
                                order=check_order,
                                item=item,
                                quantity=quantity,
                                unit_price=unit_price,
                                price=price,
                                created_by=self.request.user
                            )
                            new_price=float(check_order.order_price) + price
                            check_order.order_price = new_price
                            check_order.save()
                        else:
                            ord = MemberOrder.objects.create(
                                cooperative=member.cooperative,
                                member = member,
                                order_reference = order_reference,
                                order_price=price,
                                status = 'CREATING',
                                order_date = order_date,
                                created_by=self.request.user
                            )

                            OrderItem.objects.create(
                                order=ord,
                                item=item,
                                quantity=quantity,
                                unit_price=unit_price,
                                price=price,
                                created_by=self.request.user
                            )
                    MemberOrder.objects.filter(status='CREATING').update(status='PENDING')
                    return redirect('coop:order_list')
                except Exception as e:
                    log_error()
                    return render(request, self.template_name,
                                  {'active': 'setting', 'form': form, 'error': e})

