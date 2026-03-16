# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import pyotp
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View, ListView, RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

from conf.utils import log_error, log_debug, send_email_with_logo
from userprofile.models import *
from userprofile.forms import GroupForm, AccessLevelForm, AccessLevelGroupForm, LoginForm
from coop.models import Cooperative
from coop.utils import check_coop_url


class GroupCreateView(CreateView):
    model = Group
    # template_name = "conf/group_form.html"
    form_class = GroupForm
    success_url = reverse_lazy('profile:group_list')


class GroupUpdateView(UpdateView):
    model = Group
    # template_name = "conf/group_form.html"
    form_class = GroupForm
    success_url = reverse_lazy('conf:group_list')


class GroupListView(ListView):
    model = Group


class AccessLevelListView(ListView):
    model = AccessLevel


class AccessLevelCreateView(CreateView):
    model = AccessLevel
    form_class = AccessLevelForm
    success_url = reverse_lazy('profile:access_list')


class AccessLevelUpdateView(UpdateView):
    model = AccessLevel
    form_class = AccessLevelForm
    success_url = reverse_lazy('profile:access_list')


class AccessLevelGroupListView(ListView):
    model = AccessLevelGroup


class AccessLevelGroupCreateView(CreateView):
    model = AccessLevelGroup
    form_class = AccessLevelGroupForm
    success_url = reverse_lazy('profile:ag_list')


class AccessLevelGroupUpdateView(UpdateView):
    model = AccessLevelGroup
    form_class = AccessLevelGroupForm
    success_url = reverse_lazy('profile:ag_list')


class ChangePasswordView(View):
    template_name = 'userprofile/change_password.html'

    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            password = form.cleaned_data.get('new_password2')
            check = password_log(request.user, password)
            if check:
                user = form.save()
                data = {
                    'title': 'Password Change',
                    'status_message': 'Your Password has been updated successfully.'
                }
                messages.success(request, 'Password Updated successfully')
                password = user_form.cleaned_data.get('password')
                email = "<p>Dear {},</p> <p>Below is your new password.</p> Username: {} <br>Password: {}<br> url: {}".format(
                    user.get_full_name(), user.username, password, "https://mastercard.my-koop.com/")
                send_email_with_logo(email, user.email, "Account Creation")
                return render(request, 'account/status.html', data)
            messages.error(request,
                           'Sorry password Denied. Please use a password different from your previous %s passwords' % system_settings.password_reuse_threshold)
        return render(request, self.template_name, {'form': form})


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
            return redirect('profile:user_list')
            # messages.success(request, 'Password Updated successfully')
            # return render(request, 'account/status.html', data)
            # return redirect('profile:user_list')
            # messages.error(request, 'Sorry password Denied. Please use a password different from your previous %s passwords' % system_settings.password_reuse_threshold)
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = "userprofile/login.html"

    def get(self, request, *args, **kwargs):
        data = dict()
        log_debug('Login Page')
        data["form"] = LoginForm
        host = request.get_host()
        coop = check_coop_url(host)
        if coop:
            data["coop"] = coop
        return render(request, self.template_name, data)

    def post(self, request, *args, **kwargs):
        data = dict()
        form = LoginForm(request.POST)
        cooperative = False
        right_cooperative = None
        host = request.get_host()
        coop = check_coop_url(host)
        try:
            if form.is_valid():
                # set_login_attempt(request)
                username = form.cleaned_data.get('username', '')
                password = form.cleaned_data.get('password', '')

                user = authenticate(username=username, password=password)
                if user:
                    if user.is_active:

                        if user.profile.access_level or user.is_superuser:
                            request.session['pending_user_id'] = user.id

                            print(request.session)

                            if user.profile.enable_mfa:
                                # Optionally: send OTP via email or SMS
                                totp = user.profile.get_totp()
                                otp = totp.now()
                                print("Generated OTP:", otp)  # For testing only; send via email/SMS instead
                                self.otp_code = otp
                                self.user_email = user.email
                                self.context = {
                                    'user_name': user.username,
                                    'user_email': user.email,
                                    'otp_code': otp,
                                    'action_type': "Login",
                                    'expiry_minutes': 90,
                                }

                                self.send()

                                return redirect("verify_otp")

                            if hasattr(user.profile.access_level, 'name'):
                                if user.profile.access_level.name.lower() == "cooperative" and user.cooperative_admin:
                                    cooperative = True
                                if coop:
                                    right_cooperative = "False"
                                    if coop == user.cooperative_admin.cooperative:
                                        right_cooperative = "True"
                            if cooperative or user.profile.is_union() or user.profile.is_partner():
                                print(right_cooperative)
                                print(cooperative)
                                if cooperative:
                                    if not right_cooperative:
                                        login(request, user)
                                        return redirect('dashboard')
                                    if right_cooperative == "True":
                                        login(request, user)
                                        return redirect('dashboard')
                                    if right_cooperative == "false":
                                        data['errors'] = "Cooperative not identified. Please contact the Admin"
                                elif user.profile.is_union() or user.profile.is_partner() or user.is_superuser:
                                    login(request, user)
                                    return redirect('dashboard')
                                else:
                                    data['errors'] = "Your Cooperative Credentials Failed. Please try again"
                            else:
                                data['errors'] = "Your Cooperative not identified. Please contact the Admin"
                        else:
                            data['errors'] = "You do not permission to Signin. Please contact the Admin"
                    else:
                        data['errors'] = "Your account is inactive"
                else:
                    data['errors'] = "Username or Password invalid"

        except Exception:
            data['errors'] = "Login Error. Contact Admin"
            log_error()
        return render(request, self.template_name, {'form': form, 'errors': data, 'active': ['staff_login', 'setting']})

    def send(self):
        """Send the OTP email"""
        subject = "Your Verification Code - {}".format(self.otp_code)

        print(self.context)

        # Render HTML content
        html_content = render_to_string('email/otp_verification.html', self.context)

        # Render plain text content
        text_content = strip_tags(render_to_string('email/otp_verification.txt', self.context))

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email='Hamwe Eastafrica <noreply@hamwe.eastafrica>',
            to=[self.user_email],
            reply_to=['no-reply@my-koop.com']
        )

        # Attach HTML version
        email.attach_alternative(html_content, "text/html")

        # Add headers for better deliverability
        email.extra_headers = {
            'X-Priority': '1',
            'X-MSMail-Priority': 'High',
            'Importance': 'high'
        }

        try:
            email.send()
            print(email)
            return True
        except Exception as e:
            print("Failed to send OTP email: {}".format(e))
            return False


class VerifyOTPView(View):
    template_name = "userprofile/two_factor_verify.html"

    def get(self, request):
        print(request.session)
        if 'pending_user_id' not in request.session:
            return redirect("login")
        return render(request, self.template_name)

    def post(self, request):
        otp_code = request.POST.get("otp")
        user_id = request.session.get("pending_user_id")

        if not user_id:
            messages.error(request, "Session expired. Please login again.")
            return redirect("login")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("login")
        cooperative = False
        right_cooperative = "False"

        if user.profile.verify_totp(otp_code):
            # OTP correct → log user in
            login(request, user)
            del request.session['pending_user_id']
            messages.success(request, "Login successful.")
            # return redirect("dashboard")
            if hasattr(user.profile.access_level, 'name'):
                if user.profile.access_level.name.lower() == "cooperative" and user.cooperative_admin:
                    cooperative = True
                if coop:
                    right_cooperative = "False"
                    if coop == user.cooperative_admin.cooperative:
                        right_cooperative = "True"
            if cooperative or user.profile.is_union() or user.profile.is_partner():
                print(right_cooperative)
                print(cooperative)
                if cooperative:
                    if not right_cooperative:
                        login(request, user)
                        return redirect('dashboard')
                    if right_cooperative == "True":
                        login(request, user)
                        return redirect('dashboard')
                    if right_cooperative == "false":
                        data['errors'] = "Cooperative not identified. Please contact the Admin"
                elif user.profile.is_union() or user.profile.is_partner() or user.is_superuser:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    data['errors'] = "Your Cooperative Credentials Failed. Please try again"
            else:
                data['errors'] = "Your Cooperative not identified. Please contact the Admin"
        else:
            messages.error(request, "Invalid or expired OTP.")
            return render(request, self.template_name)

class ResendOTP(View):
    template_name = "userprofile/two_factor_verify.html"

    def get(self, request):
        print(request.session)
        if 'pending_user_id' not in request.session:
            return redirect("login")

        user = request.user
        # Optionally: send OTP via email or SMS
        totp = user.profile.get_totp()
        otp = totp.now()
        print("Generated OTP:", otp)  # For testing only; send via email/SMS instead

        return redirect("verify_otp")


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')
        # return super(LogoutView, self).get(request, *args, **kwargs)

