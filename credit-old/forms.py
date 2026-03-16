from django import forms
from django.contrib.auth.models import User
from credit.models import CreditManager, LoanRequest
from conf.utils import bootstrapify, internationalize_number, PHONE_REGEX


class CreditManagerForm(forms.ModelForm):
    class Meta:
        model = CreditManager
        exclude = ['create_date', 'update_date']


class CreditManagerUserForm(forms.ModelForm):
    confirm_password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    msisdn = forms.CharField(max_length=150)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        print(instance)
        super(CreditManagerUserForm, self).__init__(*args, **kwargs)
        if instance:
            self.fields.pop('password')
            self.fields.pop('confirm_password')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'msisdn', 'is_active', 'username', 'password',
                  'confirm_password']


bootstrapify(CreditManagerForm)
bootstrapify(CreditManagerUserForm)
