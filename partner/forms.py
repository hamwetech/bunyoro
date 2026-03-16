from django import forms
from partner.models import *
from conf.utils import bootstrapify

class PartnerForm(forms.ModelForm):
    
    class Meta:
        model = Partner
        fields = ['name', 'code', 'logo', 'phone_number', 'email', 'address', 'is_active']
        
class PartnerStaffForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=False)
    password = forms.CharField(max_length=150, widget=forms.PasswordInput(), required=False)
    confirm_password = forms.CharField(max_length=150, widget=forms.PasswordInput(), required=False)
    
    class Meta:
        model = PartnerStaff
        exclude = ['create_date', 'update_date']
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        print instance
        super(PartnerStaffForm, self).__init__(instance=instance, *args, **kwargs)
        if instance:
            self.fields.pop('password')
            self.fields.pop('confirm_password')
            self.fields['username'].initial = self.instance.user.username if self.instance.user else ''
    
    def clean(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError('Password mismatch! Please make sure the passwords are the same')

        return self.cleaned_data


bootstrapify(PartnerForm)
bootstrapify(PartnerStaffForm)