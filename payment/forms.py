import xlrd
from django import forms
from os.path import splitext
from conf.utils import bootstrapify
from payment.models import MemberPaymentTransaction
from coop.models import CooperativeMember, Cooperative

class MemberPaymentForm(forms.ModelForm):
    class Meta:
        model = MemberPaymentTransaction
        fields = ['cooperative', 'member', 'amount', 'payment_date', 'payment_method']
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(MemberPaymentForm, self).__init__(*args, **kwargs)
        
        self.fields['member'].queryset = CooperativeMember.objects.none()
        
        if 'cooperative' in self.data:
            try:
                cooperative_id = int(self.data.get('cooperative'))
                self.fields['member'].queryset = CooperativeMember.objects.filter(cooperative=cooperative_id).order_by('first_name')
            except Exception as e: #(ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            if self.instance.cooperative:
                self.fields['member'].queryset = self.instance.cooperative.member_set.order_by('first_name')
        

class BulkPaymentForm(forms.Form):
    sheetChoice = (
        ('1','sheet1'),
        ('2','sheet2'),
        ('3','sheet3'),
        ('4','sheet4'),
        ('5','sheet5'),
    )
    
    rowchoices = (
        ('1', 'Row 1'),
        ('2', 'Row 2'),
        ('3', 'Row 3'),
        ('4', 'Row 4'),
        ('5', 'Row 5')
        )
    
    choices = list()
    for i in range(65, 91):
        choices.append([i-65, chr(i)])
        
    cooperative = forms.ChoiceField(widget=forms.Select())
    payment_method = forms.ChoiceField(widget=forms.Select(), choices=(('', '------------'), ('CASH', 'CASH'), ('BANK', 'BANK'), ('MOBILE MONEY', 'MOBILE MONEY')))
    excel_file = forms.FileField()
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class':'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class':'form-control'}))
    phone_number_col = forms.ChoiceField(label='Phone Number Column', initial=0, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Members Phone Number')
    amount_col = forms.ChoiceField(label='Amount Column', initial=1, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Transaction Amount')
    transaction_date_col = forms.ChoiceField(label='Transaction Date Column', initial=2, choices=choices, required=False, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Transaction Date')
    
    def __init__(self, *args, **kwargs):
        super(BulkPaymentForm, self).__init__(*args, **kwargs)
        choices = [['','------------']]
        choices.extend([[c.id, c.name] for c in Cooperative.objects.all()])
        self.fields['cooperative'].choices = choices
    
    
    def clean(self):
        data = self.cleaned_data
        f = data.get('excel_file', None)
        ext = splitext(f.name)[1][1:].lower()
        if not ext in ["xlsx", "xls"]:
            raise forms.ValidationError(("The File type is not accepted"))
        return data


class PaymentFilterForm(forms.Form):
    search = forms.CharField(max_length=255, required=False)
    start_date = forms.CharField(max_length=160, required=False, widget=forms.TextInput(attrs={"data-uk-datepicker":"{format:'YYYY-MM-DD'}"}))
    end_date = forms.CharField(max_length=160, required=False, widget=forms.TextInput(attrs={"data-uk-datepicker":"{format:'YYYY-MM-DD'}"}))
    
    cooperative = forms.ChoiceField(widget=forms.Select(), required=False)
    payment_method = forms.ChoiceField(widget=forms.Select(), required=False, choices=(('', '------------'), ('CASH', 'CASH'), ('BANK', 'BANK'), ('MOBILE MONEY', 'MOBILE MONEY')))
    status = forms.ChoiceField(widget=forms.Select(), required=False, choices=(('', '------------'), ('PENDING', 'PENDING'), ('SUCCESSFUL', 'SUCCESSFUL'), ('FAILED', 'FAILED')))
  
    def __init__(self, *args, **kwargs):
        super(PaymentFilterForm, self).__init__(*args, **kwargs)
        choices = [['','------------']]
        choices.extend([[c.id, c.name] for c in Cooperative.objects.all()])
        self.fields['cooperative'].choices = choices

bootstrapify(MemberPaymentForm)
bootstrapify(BulkPaymentForm)
bootstrapify(PaymentFilterForm)
        
    
