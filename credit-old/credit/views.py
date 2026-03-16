from __future__ import unicode_literals
import re
import json
import xlrd
import xlwt
import datetime
from django.contrib import messages

from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils.encoding import smart_str
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View, FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from userprofile.models import Profile, AccessLevel
from credit.utils import create_loan_transaction
from credit.models import CreditManager, LoanRequest, CreditManagerAdmin, LoanTransaction, LoanRepaymentTransaction
from credit.forms import CreditManagerForm, CreditManagerUserForm, LoanUploadForm, LoanSearchForm, ApproveForm, LoanRequestForm, \
LoanRepaymentForm

from coop.utils import credit_member_account, debit_member_account
from coop.models import MemberOrder, CooperativeMember, OrderItem
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, internationalize_number, float_to_intstring, \
    get_deleted_objects, \
    get_message_template as message_template

from credit.RawFinancialAPI import RawFinancial


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)

        context.update(self.extra_context)
        return context


class CreditManagerListView(ExtraContext, ListView):
    model=CreditManager
    extra_context = {'active': ['_credit', '__cm']}


class CreditManagerCreateView(ExtraContext, CreateView):
    model = CreditManager
    form_class = CreditManagerForm
    success_url = reverse_lazy('credit:cm_list')
    extra_context = {'active': ['_credit', '__cm']}

    def get_initial(self):
        initial = super(CreditManagerCreateView, self).get_initial()
        initial['instance'] = None
        return initial


class CreditManagerUpdateView(CreditManagerCreateView, UpdateView):
    pass


class CreditManagerAdminCreateView(CreateView):
    model = CreditManager
    form_class = CreditManagerUserForm
    template_name = "credit/cm_user_form.html"
    extra_context = {'active': ['__cm']}
    success_url = reverse_lazy('credit:cm_list')


    def form_valid(self, form):
        # f = super(SupplierUserCreateView, self).form_valid(form)
        instance = None
        try:
            while transaction.atomic():
                self.object = form.save()
                if not instance:
                    self.object.set_password(form.cleaned_data.get('password'))
                self.object.save()
                pk = self.kwargs.get('cm')
                cm = get_object_or_404(CreditManager, pk=pk)
                profile = get_object_or_404(Profile, pk= self.object.id)

                profile.msisdn=form.cleaned_data.get('msisdn')
                profile.access_level=get_object_or_404(AccessLevel, name='CREDIT_MANAGER')
                profile.save()

                CreditManagerAdmin.objects.create(
                    user=self.object,
                    credit_manager = cm,
                    created_by =self.request.user
                )
        except Exception as e:
            print(e)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(CreditManagerAdminCreateView, self).get_context_data(**kwargs)
        pk = self.kwargs.get('cm')
        context['cm'] = get_object_or_404(CreditManager, pk=pk)
        return context

    def get_initial(self):
        initial = super(CreditManagerAdminCreateView, self).get_initial()
        initial['instance'] = None
        return initial

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(CreditManagerAdminCreateView, self).get_form_kwargs(*args, **kwargs)
        kwargs['instance'] = None
        return kwargs


class CreditManagerAdminListView(ExtraContext, ListView):
    model = CreditManagerAdmin
    extra_context = {'active': ['__cm']}

    def get_context_data(self, **kwargs):
        context = super(CreditManagerAdminListView, self).get_context_data(**kwargs)
        context['cm'] = self.kwargs.get('cm')
        return context


class LoanRequestListView(ExtraContext, ListView):
    model=LoanRequest
    extra_context = {'active': ['_credit', '__loan']}
    ordering = ('-id')

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(LoanRequestListView, self).dispatch(*args, **kwargs)

    def get_queryset(self, **kwargs):
        queryset = super(LoanRequestListView, self).get_queryset(**kwargs)
        search = self.request.GET.get('search')
        cooperative = self.request.GET.get('cooperative')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        status = self.request.GET.get('status')

        if search:
            queryset = queryset.filter(Q(member__surname__icontains=search)|Q(member__first_name__icontains=search)|Q(member__phone_number__icontains=search))

        if cooperative:
            queryset = queryset.filter(member__cooperative__id=cooperative)
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(request_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(request_date__gte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super(LoanRequestListView, self).get_context_data(**kwargs)
        context['form'] = LoanSearchForm
        if self.request.GET:
            context['form'] = LoanSearchForm(self.request.GET)
        return context

    def download_file(self, *args, **kwargs):

        _value = []
        columns = []
        search = self.request.GET.get('search')
        cooperative = self.request.GET.get('cooperative')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')


        profile_choices = ['member__id', 'member__first_name', 'member__surname', 'member__other_name', 'name', 'member__gender', 'member__phone_number',  'phone_number', 'request_date', 'requested_amount', 'approved_amount', 'supplier', 'agent', 'status', 'member__date_of_birth']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        # Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')

        # The response also has additional Content-Disposition header, which contains
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=MemberLoanRequests_%s.xls' % datetime.datetime.now().strftime(
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

        queryset = LoanRequest.objects.values(*profile_choices).all()

        if search:
            queryset = queryset.filter(
                Q(member__surname__icontains=search) | Q(member__first_name__icontains=search) | Q(
                    member__phone_number__icontains=search))

        if cooperative:
            queryset = queryset.filter(member__cooperative__id=cooperative)
        if start_date:
            queryset = queryset.filter(request_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(request_date__gte=end_date)

        for m in queryset:
            row_num += 1

            try:
                # Fetch the member object
                member = CooperativeMember.objects.get(
                    id=m['member__id'])  # Assuming there's a field 'member_id' in the queryset

                # Calculate the member's age
                member_age = member.get_age()
            except Exception as e:
                print(e)
                member_age = 0

            # Concatenate the name fields
            full_name = ' '.join([m['member__first_name'] if m['member__first_name'] else '',
                                  m['member__surname'] if m['member__surname'] else '',
                                  m['member__other_name'] if m['member__other_name'] else ''])

            # Format other fields as before
            row = [
                m['member__id'],
                full_name,  # Concatenated name
                '',
                '',
                m['name'],
                m['member__gender'],
                m['member__phone_number'],
                m['member__phone_number'],
                m['phone_number'],
                m['request_date'].strftime('%d-%m-%Y') if m.get('request_date') else "",
                m['requested_amount'],
                m['approved_amount'],
                m['supplier'],
                m['agent'],
                m['status'],
                m['member__date_of_birth'].strftime('%d-%m-%Y') if m.get('member__date_of_birth') else "",
                member_age
            ]

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


class LoanRequestDetailView(ExtraContext, DetailView):
    model = LoanRequest
    extra_context = {'active': ['_credit', '__loan']}
    ordering = ('-id',)


class LoanRequestEdit(ExtraContext, UpdateView):
    model = LoanRequest
    form_class = LoanRequestForm
    success_url = reverse_lazy("credit:loan_list")


class LoanRequestDeleteView(DeleteView):
    model = LoanRequest
    template_name = "confirm_delete.html"
    success_url = reverse_lazy('credit:loan_list')

    def get_context_data(self, **kwargs):
        #
        context = super(LoanRequestDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context


class ApproveLoanFormView(FormView):
    form_class = ApproveForm
    template_name = "credit/approve_form.html"

    def get_context_data(self, **kwargs):
        context = super(ApproveLoanFormView, self).get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        loan = LoanRequest.objects.get(pk=pk)
        context['loan'] = loan
        return context

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        today = datetime.datetime.today()
        amount = form.cleaned_data.get('amount')
        supplier = form.cleaned_data.get('supplier')

        lq = LoanRequest.objects.get(pk=pk)

        if amount > lq.requested_amount:
            form.add_error('amount', 'Amount is greater than offered amount')
            return super(ApproveLoanFormView, self).form_invalid(form)

        lq.confirm_date = today
        ref = genetate_uuid4()
        LoanTransaction.objects.create(
            reference=ref,  # Adjust as per your model fields
            member=lq.member,
            credit_manager=lq.credit_manager,
            amount=amount,
            transaction_type='CREDIT',  # Adjust as per your requirement
            loan=lq,
            # Add other fields as required
        )
        lq.approved_amount = amount
        lq.status = 'APPROVED'
        lq.supplier = supplier
        lq.save()
        return super(ApproveLoanFormView, self).form_valid(form)

    def get_success_url(self):
        id = self.kwargs.get('pk')
        return reverse('credit:loan_detail', kwargs={'pk': id})


class ApproveLoan(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        status = self.kwargs.get('status')
        today = datetime.datetime.today()
        try:
            lq = LoanRequest.objects.get(pk=pk)
            if status == 'APPROVED':
                lq.confirm_date = today
                transaction = LoanTransaction.objects.create(
                    reference=lq.reference,  # Adjust as per your model fields
                    member=lq.member,
                    credit_manager=lq.credit_manager,
                    amount=lq.requested_amount,
                    transaction_type='CREDIT',  # Adjust as per your requirement
                    loan=lq,
                    # Add other fields as required
                )
            if status == 'NOTTAKEN':
                lq.confirm_date = today
            if status == 'REJECTED':
                lq.confirm_date = today
            if status == "STATUS":
                status = lq.status
            lq.status = status
            lq.save()
        except Exception as e:
            log_error()

        return redirect('credit:loan_detail', pk)


class ApproveLoan_dep(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        status = self.kwargs.get('status')
        today = datetime.datetime.today()
        try:
            lq = LoanRequest.objects.get(pk=pk)
            if status == 'APPROVED':
                lq.confirm_date = today
                OrderItem.objects.filter(pk=lq.order_item.id).update(status="APPROVED")
                params = {
                    "loan": lq,
                    "member": lq.member,
                    "credit_manager": lq.credit_manager,
                    "amount": lq.requested_amount,
                    "transaction_type": 'DEBIT',
                    "created_by": request.user,
                }
                amt = create_loan_transaction(params)
                pl = {
                    "member": lq.member,
                    "amount": amt,
                    "entry_type": "CREDIT",
                    "transaction_category": "LOAN",
                    "description": "Loan request approved",
                    "created_by": request.user,
                }
                credit_member_account(pl)

                pld = {
                    "member": lq.member,
                    "amount": amt,
                    "entry_type": "DEBIT",
                    "transaction_category": "ORDER",
                    "description": "Order for item %s" % (lq.order_item.item.name),
                    "created_by": request.user,
                }
                debit_member_account(pld)

            if status == 'REJECTED':
                lq.confirm_date = today
            if status == "STATUS":
                status = lq.status
                rf = RawFinancial()
                st = rf.loan_status(lq.loan_request_id)
                if "loan_status" in st:
                    lq.response = "{} <br>======<br> {}".format(lq.response, st)
                    if st['loan_status'] == "rejected":
                        status = "REJECTED"
                    if st['loan_status'] == "approved":
                        status = "APPROVED"
                        lq.confirm_date = today
                        OrderItem.objects.filter(pk=lq.order_item.id).update(status="APPROVED")
                        params = {
                            "loan": lq,
                            "member": lq.member,
                            "credit_manager": lq.credit_manager,
                            "amount": lq.requested_amount,
                            "transaction_type": 'DEBIT',
                            "created_by": request.user,
                        }
                        amt = create_loan_transaction(params)
                        pl = {
                            "member": lq.member,
                            "amount": amt,
                            "entry_type": "CREDIT",
                            "transaction_category": "LOAN",
                            "description": "Loan request approved",
                            "created_by": request.user,
                        }
                        credit_member_account(pl)

                        pld = {
                            "member": lq.member,
                            "amount": amt,
                            "entry_type": "DEBIT",
                            "transaction_category": "ORDER",
                            "description": "Order for item %s" % (lq.order_item.item.name),
                            "created_by": request.user,
                        }
                        debit_member_account(pld)
            lq.status = status
            lq.save()
        except Exception as e:
            log_error()

        return redirect('credit:loan_detail', pk)


class LoanTransactionListView(ExtraContext, ListView):
    model=LoanTransaction
    extra_context = {'active': ['_credit', '__loan_transaction']}
    ordering = ('-id')


class LoanRequestUploadView(ExtraContext, View):
    template_name = "credit/loan_upload_view.html"

    def get(self, request, **kwargs):
        context = dict()
        form = LoanUploadForm
        context['form'] = form
        return render(request, self.template_name, context)

    def post(self, request, **kwargs):
        context = dict()
        form = LoanUploadForm(request.POST, request.FILES)

        if form.is_valid():

            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1

            proceed = form.cleaned_data['proceed']
            credit_manager = form.cleaned_data['credit_manager']
            name_col = int(form.cleaned_data['name_col'])
            phone_number_col = int(form.cleaned_data['phone_number_col'])
            request_date_col = int(form.cleaned_data['request_date_col'])
            loan_amount_col = int(form.cleaned_data['loan_amount_col'])
            agent_col = int(form.cleaned_data['agent_col'])

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            payment_list = []
            members_not_found = []
            member = None

            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i + 1

                    name = smart_str(row[name_col].value).strip()
                    phone_number = smart_str(row[phone_number_col].value).strip()
                    # request_date = smart_str(row[request_date_col].value).strip()
                    loan_amount = smart_str(row[loan_amount_col].value).strip()
                    agent = smart_str(row[agent_col].value).strip()

                    phone_number = "1111" if phone_number == "" else phone_number

                    if not re.search('^[0-9]+$', phone_number, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Phone Number (row %d)' % (phone_number, i + 1)
                        print(data)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    if not re.search('^[0-9\.]+$', loan_amount, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Amount Figure (row %d)' % (loan_amount, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    request_date = (row[request_date_col].value)
                    if request_date:
                        try:
                            date_str = datetime.datetime(*xlrd.xldate_as_tuple(int(request_date), book.datemode))
                            # transaction_date = date_str.strftime("%Y-%m-%d")
                            # date_str = datetime(*xlrd.xldate_as_tuple(request_date, book.datemode))
                            request_date = date_str.strftime("%Y-%m-%d %H:%M")
                        except Exception as e:
                            data['errors'] = '"%s" is not a valid Request Date (row %d): %s' % \
                                             (request_date, i + 1, e)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})
                    phn = None
                    if phone_number != str(1111):
                        phn = internationalize_number(phone_number)
                        # member = CooperativeMember.objects.filter(Q(user_id=phone_number)|Q(member_id=phone_number)|Q(phone_number=phn)|Q(id=phone_number))
                    member = None
                    members = CooperativeMember.objects.filter(phone_number=phn)
                    if members.count() == 1:
                        member = members[0]
                    else:
                        name = name.split(' ')
                        surname = name[0]
                        first_name = name[1] if len(name) > 1 else None
                        other_name = name[2] if len(name) > 2 else None
                        mbrs = CooperativeMember.objects.filter(first_name__iexact=first_name, surname__iexact=surname)
                        if mbrs.count() > 0:
                            member = mbrs[0]
                        else:
                            members_not_found.append('"%s" Member record not found (row %d)' % (name, i + 1))
                            # data['errors'] = '"%s %s" Member record not found (row %d)' % (last_name, first_name, i + 1)
                            # return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    q = {'member': member,
                         'name': name,
                         'loan_amount': loan_amount,
                         'phone_number': phn,
                         'agent': agent,
                         'request_date': request_date,
                         }
                    payment_list.append(q)

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form':form, 'error': err})

            if len(members_not_found) > 0:
                data['missing_members'] = '<br>'.join(members_not_found)
                data['missing_members_count'] = len(members_not_found)
            if not proceed:
                if len(members_not_found) > 0:
                    data['missing_members'] = '<br>'.join(members_not_found)
                    data['missing_members_count'] = len(members_not_found)
                return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

            print(payment_list)
            if payment_list:
                with transaction.atomic():
                    try:
                        do = None

                        for nc in payment_list:
                            member = nc.get('member')
                            requested_amount = nc.get('loan_amount')
                            request_date = nc.get('request_date') if nc.get('request_date') != '' else None
                            phone_number = nc.get('phone_number')
                            agent = nc.get('agent')
                            name = nc.get('name')

                            if member:
                                lqs = LoanRequest.objects.filter(member__phone_number=phone_number)
                                if not lqs.exists():
                                    LoanRequest.objects.create(
                                        reference=generate_alpanumeric("LR",9),
                                        credit_manager=credit_manager,
                                        member=member,
                                        name=name,
                                        requested_amount=requested_amount,
                                        request_date=request_date,
                                        agent=agent,
                                    )
                        if len(members_not_found) > 0:
                            messages.warning(request, data)
                        return redirect('credit:loan_list')
                    except Exception as err:
                        log_error()
                        data['error'] = err
        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})


class LoanRepaymentFormView(CreateView):
    model = LoanRepaymentTransaction
    form_class = LoanRepaymentForm
    success_url = reverse_lazy("credit:loan_list")

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        req = LoanRequest.objects.get(pk=pk)

        repayment_amount = form.instance.amount_paid
        approved_amount = req.approved_amount
        amount_paid = req.amount_paid

        dd = approved_amount - amount_paid
        bal = dd - repayment_amount
        form.instance.balance = bal

        req.amount_paid =  repayment_amount + amount_paid
        req.save()

        return super(LoanRepaymentFormView, self).form_valid(form)

    def get_initial(self):
        pk = self.kwargs.get('pk')
        print(pk)
        return {
            'request': pk
        }

    def get_form(self, form_class=None):
        """Limit ForeignKey choices dynamically"""
        form = super(LoanRepaymentFormView, self).get_form(form_class)
        form.fields['request'].queryset = LoanRequest.objects.filter(status='APPROVED')  # You can filter here if needed
        return form


class LoanRepaymentListView(ListView):
    model = LoanRepaymentTransaction