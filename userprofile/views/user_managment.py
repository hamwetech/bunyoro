# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import transaction
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import View, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, FormView
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse

from conf.utils import log_error, log_debug, send_email_with_logo
from userprofile.models import Profile, Device, AssignedCards, DeviceLocation
from userprofile.forms import UserProfileForm, UserForm, CooperativeAdminForm, DeviceForm, AssignedCardsForm, BulkDeviceForm
from coop.models import OtherCooperativeAdmin, Cooperative, CooperativeAdmin


# class UserProfileCreateView(CreateView):
#     model = Profile
#     form_class = UserProfileForm
#     success_url = reverse_lazy('profile:user_list')


class UserProfileCreateView(View):
    template_name = "userprofile/profile_form.html"

    def get(self, request, *arg, **kwarg):
        pk = self.kwargs.get('pk')
        instance = None
        profile = None
        coop_admin = None
        initial = None
        if pk:
            user = User.objects.get(pk=pk)
            if user:
                instance = user
                other = OtherCooperativeAdmin.objects.values_list('cooperative__id', flat=True).filter(user=instance)
                print(other)
                initial = {"other_cooperative": [x for x in other]}
                profile = instance.profile
                if hasattr(instance, 'cooperative_admin'):
                    coop_admin = instance.cooperative_admin

        user_form = UserForm(instance=instance)
        profile_form = UserProfileForm(instance=profile, initial=initial, request=self.request)

        coop_form = CooperativeAdminForm(instance=coop_admin, request=self.request)
        data = {'user_form': user_form, 'profile_form': profile_form, 'coop_form': coop_form}
        return render(request, self.template_name, data)

    def post(self, request, *arg, **kwargs):
        pk = self.kwargs.get('pk')
        instance = None
        profile = None
        coop_admin = None
        errors = dict()

        if pk:
            instance = User.objects.filter(pk=pk)
            if instance.exists():
                instance = instance[0]
                profile = instance.profile
                if hasattr(instance, 'cooperative_admin'):
                    coop_admin = instance.cooperative_admin
        user_form = UserForm(request.POST, instance=instance)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile, request=self.request)
        coop_form = CooperativeAdminForm(request.POST, instance=coop_admin, request=self.request)

        if user_form.is_valid() and profile_form.is_valid() and coop_form.is_valid():
            try:
                with transaction.atomic():

                    if profile_form.cleaned_data.get('access_level'):
                        if coop_form.cleaned_data.get('cooperative'):
                            print(profile_form.cleaned_data.get('access_level').name.lower() == 'cooperative' or profile_form.cleaned_data.get('access_level').name.lower() == 'agent')
                            if profile_form.cleaned_data.get('access_level').name.lower() == 'cooperative' or profile_form.cleaned_data.get('access_level').name.lower() == 'agent':
                                pass
                            else:
                                errors['errors'] = "Only Cooperate Level Users can be assigned to a Cooperative"

                    if not errors:
                        user = user_form.save(commit=False);
                        if not instance:
                            user.set_password(user.password)
                        user.save()
                        if not pk:
                            profile_form = UserProfileForm(request.POST, request.FILES, instance=user.profile, request=self.request)
                        profile_form.save()

                        if coop_form.cleaned_data.get('cooperative'):
                            c = coop_form.save(commit=False)
                            c.user = user
                            c.save()

                        if profile_form.cleaned_data.get('other_cooperative'):
                            OtherCooperativeAdmin.objects.filter(user=user).delete()
                            for c in profile_form.cleaned_data.get('other_cooperative'):
                                OtherCooperativeAdmin.objects.create(
                                    user=user,
                                    cooperative=Cooperative.objects.get(pk=c),
                                )
                        try:
                            if not pk:
                                password = user_form.cleaned_data.get('password')
                                email = "<p>Dear {},</p> <p>Welcome to My-Koop (Mastercard) below are your credentials.</p> Username: {} <br>Password: {}<br> url: {}".format(user.get_full_name(), user.username, password, "https://mastercard.my-koop.com/")
                                send_email_with_logo(email, user.email, "Account Creation")
                        except Exception as e:
                            log_error()

                        return redirect('profile:user_list')
            except Exception as e:
                log_error()
                errors['errors'] = "Error %s" % e
        data = {'user_form': user_form, 'profile_form': profile_form, 'coop_form': coop_form}
        data.update(errors)
        return render(request, self.template_name, data)


class UserProfileUpdateView(UpdateView):
    model = Profile
    form_class = UserProfileForm
    success_url = reverse_lazy('profile:user_list')

class UserProfileListView(ListView):
    model = Profile

    def get_queryset(self):
        queryset = super(UserProfileListView, self).get_queryset()
        u = []
        if hasattr(self.request.user, 'cooperative_admin'):
            [u.append(x.user) for x in CooperativeAdmin.objects.filter(cooperative=self.request.user.cooperative_admin.cooperative)]
            print(u)
            queryset = queryset.filter(user__in=u)
        return queryset


class DeviceCreateView(CreateView):
    model = Device
    form_class = DeviceForm
    extra_context = {'active': ['_device', '__Item']}
    success_url = reverse_lazy('profile:device_list')


class DeviceUpdateView(UpdateView):
    model = Device
    form_class = DeviceForm
    extra_context = {'active': ['_device', '__Item']}
    success_url = reverse_lazy('profile:device_list')


class DeviceListView(ListView):
    model = Device
    extra_context = {'active': ['_device', '__Item']}

    def get_queryset(self):
        queryset = super(DeviceListView, self).get_queryset()
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(in_charge=user)
        return queryset


class AssignedCardsCreateView(CreateView):
    model = AssignedCards
    form_class = AssignedCardsForm
    extra_context = {'active': ['_device', '__Item']}
    success_url = reverse_lazy('profile:assign_cards_list')

    def form_valid(self, form):
        form.created_by = self.request.user
        return super(AssignedCardsCreateView, self).form_valid(form)


class AssignedCardsUpdateView(UpdateView):
    model = AssignedCards
    form_class = AssignedCardsForm
    extra_context = {'active': ['_device', '__Item']}
    success_url = reverse_lazy('profile:assign_cards_list')


class AssignedCardsListView(ListView):
    model = AssignedCards
    extra_context = {'active': ['_device', '__Item']}


class DeviceMapView(TemplateView):
    template_name = "userprofile/device_map.html"

    def get_context_data(self, **kwargs):
        context = super(DeviceMapView, self).get_context_data(**kwargs)
        return context


class BulkAddDeviceView(FormView):
    template_name = "userprofile/bulk_device_add.html"
    form_class = BulkDeviceForm
    success_url = reverse_lazy('profile:device_list')

    def form_valid(self, form):
        in_charge = form.cleaned_data.get('in_charge')
        devices_text = form.cleaned_data.get('device')
        print(devices_text)
        devices_list = [device.strip() for device in devices_text.split('\n') if device.strip()]
        device_count = 0
        try:
            with transaction.atomic():
                for device in devices_list:
                    Device.objects.create(in_charge=in_charge, device_id=device)
                    device_count += 1
                messages.success(self.request, '%s Devices Added' % device_count)
        except Exception as e:
            messages.error(self.request, 'Devices add Error: %s' % e)
            return super(BulkAddDeviceView, self).form_invalid(form)
        return super(BulkAddDeviceView, self).form_valid(form)


def get_device_map(request):
    devices = Device.objects.all()
    data = []
    for d in devices:
        location = DeviceLocation.objects.filter(assigned_to=d.assigned_to).order_by('-id')
        # location = DeviceLocation.objects.all().order_by('-id')
        if location.exists():
            loc = location[0]
            if loc.longitude:
                data.append({"name": loc.assigned_to.username, "gps": "{},{}".format(loc.latitude, loc.longitude)})

    print(data)
    return JsonResponse(data, safe=False)


