# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import magic
import re
import xlrd
import xlwt
import datetime
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import smart_str
from django.db import transaction
from django.db.models import Count, Q
from django.views.generic import View, ListView, FormView, DetailView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from conf.utils import log_debug, log_error, get_deleted_objects, get_consontant_upper
from conf.models import District, County, SubCounty
from coop.models import *
from coop.forms import *
from django.http import JsonResponse, HttpResponse
from userprofile.models import Profile, AccessLevel
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context


class AgentListView(ExtraContext, ListView):
    template_name = 'coop/agents_list.html'

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(AgentListView, self).dispatch(*args, **kwargs)

    def get(self, request, **kwargs):

        name = self.request.GET.get('name')
        phone_number = self.request.GET.get('phone_number')
        cooperative = self.request.GET.get('cooperative')
        end_date = self.request.GET.get('end_date')
        start_date = self.request.GET.get('start_date')

        agents = Agent.objects.all()
        if phone_number:
            agents = agents.filter(phone_number=phone_number)

        if name:
            agents = agents.filter(Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name))

        if self.request.user.profile.district_incharge.all().count() > 0:
            agents = agents.filter(district__id__in=self.request.user.profile.district_incharge.all())

        agent_summary = []
        for a in agents:
            queryset = CooperativeMember.objects.filter(create_by=a.user)

            if start_date:
                queryset = queryset.filter(create_date__gte=start_date)

            if end_date:
                queryset = queryset.filter(create_date__lte="%s 23:59:59" % end_date)

            if cooperative:
                queryset = queryset.filter(cooperative_id=cooperative)
            agent_summary.append({'agent': a, 'members': queryset.count()})


        data = {
            'agent_summary': agent_summary,
            'form': AgentSearchForm(request.GET),
            'active': ['_agent']
        }
        return render(request, self.template_name, data)


    def download_file(self, *args, **kwargs):

        _value = []
        columns = []
        name = self.request.GET.get('name')
        phone_number = self.request.GET.get('phone_number')
        cooperative = self.request.GET.get('cooperative')
        end_date = self.request.GET.get('end_date')
        start_date = self.request.GET.get('start_date')

        profile_choices = ['user__id', 'user__first_name', 'user__last_name', 'sex',
                           'date_of_birth',
                           'msisdn', 'nin', 'district__name', 'sub_county__name', 'village', 'gps_coodinates',
                           'supervisor__last_name', 'create_date']

        columns += [self.replaceMultiple(c, ['_', '__name'], ' ').title() for c in profile_choices]
        columns += ['Total Farmers', 'Carded Farmers']
        # Gather the Information Found
        # Create the HttpResponse object with Excel header.This tells browsers that
        # the document is a Excel file.
        response = HttpResponse(content_type='application/ms-excel')

        # The response also has additional Content-Disposition header, which contains
        # the name of the Excel file.
        response['Content-Disposition'] = 'attachment; filename=Agents_CommunityPass_%s.xls' % datetime.now().strftime(
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

        _members = Agent.objects.values(*profile_choices).all()

        if phone_number:
            _members = _members.filter(phone_number=phone_number)

        if name:
            _members = _members.filter(Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name))

        if self.request.user.profile.district_incharge.all().count() > 0:
            _members = _members.filter(district__id__in=self.request.user.profile.district_incharge.all())

        agent_summary = []
        # for a in _members:
        #     queryset = CooperativeMember.objects.filter(create_by=a.user)
        #
        #     if start_date:
        #         queryset = queryset.filter(create_date__gte=start_date)
        #
        #     if end_date:
        #         queryset = queryset.filter(create_date__lte=end_date)
        #
        #     if cooperative:
        #         queryset = queryset.filter(cooperative_id=cooperative)
        #     agent_summary.append({'agent': a, 'members': queryset.count()})

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
            coop_member = CooperativeMember.objects.filter(create_by=m['user__id'])

            if start_date:
                coop_member = coop_member.filter(create_date__gte=start_date)

            if end_date:
                coop_member = coop_member.filter(create_date__lte="%s 23:59:59" % end_date)

            if cooperative:
                coop_member = coop_member.filter(cooperative_id=cooperative)

            carded = coop_member.exclude(Q(consumer_device_id="") | Q(consumer_device_id="null"))
            row.append(coop_member.count())
            row.append(carded.count())

            for col_num in range(len(row)):
                worksheet.write(row_num, col_num, row[col_num])
        workbook.save(response)
        return response

    def get_village(self, id):
        try:
            village = Village.objects.get(name=id)
            village = village.name
        except Exception as e:
            village = ""
        print(village)
        return village

    def replaceMultiple(self, mainString, toBeReplaces, newString):
        # Iterate over the strings to be replaced
        for elem in toBeReplaces:
            # Check if string is in the main string
            if elem in mainString:
                # Replace the string
                mainString = mainString.replace(elem, newString)

        return mainString


class AgentCreateFormView(ExtraContext, View):
    template_name = "coop/agent_form.html"
    # form_class = AgentForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        first_form = AgentForm()
        second_form = ProfileForm()
        initial = {}
        if pk:
            user = get_object_or_404(User, pk=pk)
            fgs = FarmerGroupAdmin.objects.filter(user=user)
            initial['farmer_group'] = [i.farmer_group.id for i in fgs]
            initial['district_incharge'] = [d.id for d in user.profile.district_incharge.all()]
            print(initial)
            first_form = AgentForm(instance=user, initial=initial)
            second_form = ProfileForm(instance=user.profile, initial=initial)
        return render(self.request, self.template_name, {"first_form": first_form,  "second_form": second_form})

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        first_form = AgentForm(request.POST)
        second_form = ProfileForm(request.POST, request.FILES)
        if pk:
            user = get_object_or_404(User, pk=pk)
            first_form = AgentForm(request.POST, instance=user)
            second_form = ProfileForm(request.POST, request.FILES, instance=user.profile)

        if first_form.is_valid() and second_form.is_valid():
            try:
                while transaction.atomic():
                    user = first_form.save()
                    if pk:
                        user.set_password(first_form.cleaned_data.get('password'))
                    user.save()
                    profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile)
                    if profile_form.is_valid():
                        p = profile_form.save(commit=False)
                        p.access_level = get_object_or_404(AccessLevel, name="AGENT")
                        p.save()

                        fgs = profile_form.cleaned_data.get('farmer_group')
                        district_incharge = profile_form.cleaned_data.get('district_incharge')
                        print(district_incharge)
                        p.district_incharge.clear()
                        for district in district_incharge:
                            p.district_incharge.add(district)

                        if fgs:
                            for fg in fgs:
                                FarmerGroupAdmin.objects.create(
                                    user=user,
                                    farmer_group=get_object_or_404(FarmerGroup, pk=fg),
                                    created_by=self.request.user
                                )

                    return redirect('coop:agent_list')
            except Exception as e:
                first_form.add_error(None, 'Error: %s.' % e)
                log_error()
                print(e)
                return render(self.request, self.template_name, {"first_form": first_form,  "second_form": second_form})
        else:
            print(second_form.non_field_errors )
            return render(self.request, self.template_name, {"first_form": first_form,  "second_form": second_form})


class AgentCreateFormView__D(ExtraContext, FormView):
    template_name = "coop/agent_form.html"
    form_class = AgentForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    def form_valid(self, form):

        # f = super(SupplierUserCreateView, self).form_valid(form)
        instance = None
        try:
            while transaction.atomic():
                self.object = form.save()
                if not instance:
                    self.object.set_password(form.cleaned_data.get('password'))
                self.object.save()

                profile = self.object.profile

                profile.msisdn=form.cleaned_data.get('msisdn')
                profile.sex=form.cleaned_data.get('sex')
                profile.nin=form.cleaned_data.get('nin')
                profile.date_of_birth=form.cleaned_data.get('date_of_birth')

                profile.access_level=get_object_or_404(AccessLevel, name="AGENT")
                profile.save()

                fgs = form.cleaned_data.get('farmer_group')
                districts = form.cleaned_data.get('district')
                for district in districts:
                    profile.district_incharge.add(district)

                for fg in fgs:
                    FarmerGroupAdmin.objects.create(
                        user=self.object,
                        farmer_group = get_object_or_404(FarmerGroup, pk=fg),
                        created_by =self.request.user
                    )
                return super(AgentCreateFormView, self).form_valid(form)
        except Exception as e:
            form.add_error(None, 'Error: %s.' % e)
            log_error()
            return super(AgentCreateFormView, self).form_invalid(form)


class AgentUpdateFormView(ExtraContext, UpdateView):
    model = User
    template_name = "coop/agent_form.html"
    form_class = AgentUpdateForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    # def get_form(self, form_class):
    #     form = super(AgentUpdateFormView, self).get_form(form_class)
    #
    def form_invalid(self, form):
        print('Error')
        return super(AgentUpdateFormView, self).form_invalid(form)

    def form_valid(self, form):
        # f = super(SupplierUserCreateView, self).form_valid(form)
        print('FF')
        instance = None
        try:
            while transaction.atomic():
                super(AgentUpdateFormView, self).form_valid(form)
                # self.object = form.save()
                if not instance:
                    self.object.set_password(form.cleaned_data.get('password'))
                    self.object.save()

                profile = self.object.profile

                profile.msisdn=form.cleaned_data.get('msisdn')

                profile.access_level=get_object_or_404(AccessLevel, name="AGENT")
                profile.save()

                fgs = form.cleaned_data.get('farmer_group')

                districts = form.cleaned_data.get('district')
                if districts:
                    profile.district.clear()
                    for district in districts:
                        print(district)
                        profile.district.add(district)
                        profile.save()

                FarmerGroupAdmin.objects.filter(user=self.object).delete()
                for fg in fgs:
                    FarmerGroupAdmin.objects.create(
                        user=self.object,
                        farmer_group = get_object_or_404(FarmerGroup, pk=fg),
                        created_by =self.request.user
                    )
                return redirect('coop:agent_list')
        except Exception as e:
            log_error()
            form.add_error(None, 'Error: %s.' % e)
            return super(AgentUpdateFormView, self).form_invalid(form)

    def get_initial(self):
        initial = super(AgentUpdateFormView, self).get_initial()
        user = User.objects.get(pk=self.kwargs.get('pk'))
        fgs=FarmerGroupAdmin.objects.filter(user=user)
        initial['msisdn'] = user.profile.msisdn
        initial['farmer_group'] = [i.farmer_group.id for i in fgs]
        initial['district'] = [d.id for d in user.profile.district.all()]

        return initial
    #
    # def get_form_kwargs(self):
    #     kwargs = super(AgentUpdateFormView, self).get_form_kwargs()
    #     kwargs['instance'] = User.objects.get(pk=self.kwargs.get('pk'))
    #     return kwargs


class AgentDetailView(ExtraContext, DetailView):
    model = User
    template_name = "coop/agent_detail_view.html"


class AgentUploadView(View):
    template_name = 'coop/upload_agents.html'

    def get(self, request, *arg, **kwargs):
        data = dict()
        data['form'] = AgentUploadForm()
        data['active'] = ['_agent']
        return render(request, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = AgentUploadForm(request.POST, request.FILES)
        if form.is_valid():

            f = request.FILES['excel_file']

            path = f.temporary_file_path()
            index = int(form.cleaned_data['sheet']) - 1
            startrow = int(form.cleaned_data['row']) - 1
            name_col = int(form.cleaned_data['name_col'])
            email_column = int(form.cleaned_data['email_column'])
            phone_number_col = int(form.cleaned_data['phone_number_col'])
            district_col = int(form.cleaned_data['district_col'])
            username_col = int(form.cleaned_data['username_col'])
            password_col = int(form.cleaned_data['password_col'])

            book = xlrd.open_workbook(filename=path, logfile='/tmp/xls.log')
            sheet = book.sheet_by_index(index)
            rownum = 0
            data = dict()
            agent_list = []
            for i in range(startrow, sheet.nrows):
                try:
                    row = sheet.row(i)
                    rownum = i + 1
                    name = smart_str(row[name_col].value).strip()

                    if not re.search('^[0-9A-Z\s\(\)\-\.]+$', name, re.IGNORECASE):
                        data['errors'] = '"%s" is not a valid Name (row %d)' % \
                                         (name, i + 1)
                        return render(request, self.template_name, {'active': 'system', 'form': form, 'error': data})

                    email = smart_str(row[email_column].value).strip()

                    if email:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', email, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid Email (row %d)' % \
                                             (email, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})


                    phone_number = smart_str(row[phone_number_col].value).strip()

                    if phone_number:
                        try:
                            phone_number = int(row[phone_number_col].value)
                        except Exception:
                            data['errors'] = '"%s" is not a valid Phone number (row %d)' % \
                                             (phone_number, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    district = smart_str(row[district_col].value).strip()

                    if district:
                        if not re.search('^[A-Z\s\(\)\-\.]+$', district, re.IGNORECASE):
                            data['errors'] = '"%s" is not a valid District (row %d)' % \
                                             (district, i + 1)
                            return render(request, self.template_name,
                                          {'active': 'system', 'form': form, 'error': data})

                    username = smart_str(row[username_col].value).strip()

                    if not username:
                        data['errors'] = 'Username is missing at (row %d)' % \
                                         (i + 1)
                        return render(request, self.template_name,
                                      {'active': 'system', 'form': form, 'error': data})

                    password = smart_str(row[password_col].value).strip()

                    if not password:
                        data['errors'] = 'Password is missing at (row %d)' % \
                                         (i + 1)
                        return render(request, self.template_name,
                                      {'active': 'system', 'form': form, 'error': data})

                    q = {'name': name, 'email': email, 'username': username, 'password': password, 'phone_number': phone_number, 'district': district,}
                    agent_list.append(q)

                except Exception as err:
                    log_error()
                    return render(request, self.template_name, {'active': 'setting', 'form': form, 'error': '%s on (row %d)' % (err, i + 1)})
            if agent_list:
                with transaction.atomic():
                    try:
                        for c in agent_list:

                            do = None

                            name = c.get('name').split(' ')
                            surname = name[0]
                            first_name = name[1] if len(name) > 1 else None
                            other_name = name[2] if len(name) > 2 else None
                            email = c.get('email')
                            username = c.get('username')
                            password = c.get('password')
                            phone_number = c.get('phone_number')

                            if district:
                                dl = [dist for dist in District.objects.filter(name__iexact=district)]
                                do = dl[0] if len(dl) > 0 else None

                            if not User.objects.filter(username=username).exists():
                                user = User.objects.create(
                                    first_name=first_name,
                                    last_name=surname,
                                    email=email,
                                    username=username,
                                    is_active=True,
                                )

                                user.set_password(password)
                                user.save()

                                profile = user.profile
                                profile.msisdn = phone_number
                                profile.district.add(do)
                                profile.access_level = get_object_or_404(AccessLevel, name="AGENT")
                                profile.save()

                        return redirect('coop:agent_list')
                    except Exception as err:
                        log_error()
                        data['error'] = err

        data['form'] = form
        data['active'] = ['_agent']
        return render(request, self.template_name, data)


class AssignDeviceFormView(FormView):
    template_name = "coop/form.html"
    form_class = AssignDeviceForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        device = form.cleaned_data.get('device')
        obj = Device.objects.get(pk=device)
        obj.assigned_to = get_object_or_404(User, pk=pk)
        obj.save()
        return super(AssignDeviceFormView, self).form_valid(form)

    def get_initial(self):
        initial = super(AssignDeviceFormView, self).get_initial()
        user = User.objects.get(pk=self.kwargs.get('pk'))
        device = Device.objects.filter(assigned_to=user)
        if device.exists():
            print(device[0].id)
            initial['device'] = device[0].id
        return initial

    def get_context_data(self, *args, **kwargs):
        context = super(AssignDeviceFormView, self).get_context_data(*args, **kwargs)
        context['title'] = "Assign Device"
        return context


class AssignCardsFormView(FormView):
    template_name = "coop/form.html"
    form_class = AssignCardsForm
    extra_context = {'active': ['_agent']}
    success_url = reverse_lazy('coop:agent_list')

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        card_number = form.cleaned_data.get('card_number')
        user = get_object_or_404(User, pk=pk)
        cards = AssignedCards.objects.filter(assigned_to=user)
        if cards.exists():
            card = cards[0]
            card.number_of_cards = card_number
            card.save()
        else:
            AssignedCards.objects.create(assigned_to=user, number_of_cards=card_number)

        return super(AssignCardsFormView, self).form_valid(form)

    def get_initial(self):
        initial = super(AssignCardsFormView, self).get_initial()
        user = User.objects.get(pk=self.kwargs.get('pk'))
        cards = AssignedCards.objects.filter(assigned_to=user)
        if cards.exists():
            print(cards[0].number_of_cards)
            initial['number_of_cards'] = cards[0].number_of_cards
        return initial

    def get_context_data(self, *args, **kwargs):
        context = super(AssignCardsFormView, self).get_context_data(*args, **kwargs)
        context['title'] = "Assign Card"
        return context


class AdminChangePasswordView(View):
    template_name = 'userprofile/change_password.html'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        user = User.objects.get(pk=pk)
        form = SetPasswordForm(user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        __user = User.objects.get(pk=pk)
        form = SetPasswordForm(__user, request.POST)

        if form.is_valid():
            user = form.save()
            data = {
                'title': 'Password Change',
                'status_message': 'Your Password has been updated successfully.'
            }
            messages.success(request, 'Password Updated successfully')
            return redirect('coop:agent_list')
            # messages.success(request, 'Password Updated successfully')
            # return render(request, 'account/status.html', data)
            # return redirect('profile:user_list')
            # messages.error(request, 'Sorry password Denied. Please use a password different from your previous %s passwords' % system_settings.password_reuse_threshold)
        return render(request, self.template_name, {'form': form})


class AgentMapView(TemplateView):
    template_name = "coop/agent_map.html"

    def get_context_data(self, **kwargs):
        context = super(AgentMapView, self).get_context_data(**kwargs)
        return context


def get_agent_location(request):
    profile = Agent.objects.all().order_by('-id')
    data = []
    for p in profile:
        if p.gps_coodinates:
            data.append({"name": p.user.get_full_name(), "gps": "{}".format(p.gps_coodinates)})
    return JsonResponse(data, safe=False)
