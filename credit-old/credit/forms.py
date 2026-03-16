from django import forms
from django.contrib.auth.models import User
from credit.models import CreditManager, LoanRequest, LoanRepaymentTransaction
from conf.utils import bootstrapify, internationalize_number, PHONE_REGEX
from coop.models import CooperativeMember


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


class LoanUploadForm(forms.Form):
    sheetChoice = (
        ('1', 'sheet1'),
        ('2', 'sheet2'),
        ('3', 'sheet3'),
        ('4', 'sheet4'),
        ('5', 'sheet5'),
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
        choices.append([i - 65, chr(i)])

    excel_file = forms.FileField()
    credit_manager = forms.ModelChoiceField(queryset=CreditManager.objects.all())
    proceed = forms.BooleanField(label='Proceed if farmer is not found', required=False)
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class': 'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class': 'form-control'}))
    name_col = forms.ChoiceField(label='Name Column', initial=0, choices=choices,
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 help_text='The column containing the Last Name')
    phone_number_col = forms.ChoiceField(label='Phone Number Column', initial=1, choices=choices,
                                       widget=forms.Select(attrs={'class': 'form-control'}),
                                       help_text='The column containing the Phone Number Name')
    request_date_col = forms.ChoiceField(label='Request Date Column', initial=2, choices=choices,
                                      widget=forms.Select(attrs={'class': 'form-control'}),
                                      help_text='The column containing the Village')
    agent_col = forms.ChoiceField(label='Agent Column', initial=3, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Loan Agent')
    loan_amount_col = forms.ChoiceField(label='Loan Amount Column', initial=4, choices=choices,
                                     widget=forms.Select(attrs={'class': 'form-control'}),
                                     help_text='The column containing the Loan Amount')


class LoanSearchForm(forms.Form):
    search = forms.CharField(max_length=150, required=False)
    cooperative = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    start_date = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'id': 'uk_dp_start',
                                                                                               'data-uk-datepicker': "{format:'YYYY-MM-DD'}",
                                                                                               'autocomplete': "off"}))
    end_date = forms.CharField(max_length=150, required=False,
                               widget=forms.TextInput(attrs={'class': 'some_class', 'id': 'uk_dp_end',
                                                             'data-uk-datepicker': "{format:'YYYY-MM-DD'}",
                                                             'autocomplete': "off"}))
    status = forms.ChoiceField(widget=forms.Select(), required=False, choices=(('', '-----'), ('PENDING', 'PENDING'), ('PROCESSING', 'PROCESSING'),
                                                      ('ACCEPTED', 'ACCEPTED'), ('NOT TAKEN', 'NOTTAKEN'),
                                                      ('INPROGRESS', 'INPROGRESS'), ('PAID', 'PAID'),
                                                      ('APPROVED', 'APPROVED')))

    def __init__(self,  *args, **kwargs):
        super(LoanSearchForm, self).__init__(*args, **kwargs)

        qs = LoanRequest.objects.values('member__cooperative__id', 'member__cooperative__name').distinct()
        print(qs)
        choices = [['', 'Cooperative']]
        for q in qs:
            choices.append([q['member__cooperative__id'], q['member__cooperative__name']])
        self.fields['cooperative'].choices = choices


class ApproveForm(forms.Form):
    amount = forms.IntegerField()
    supplier = forms.CharField(max_length=255)


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = LoanRequest
        exclude = ['create_date', 'update_date']

    def __init__(self, *args, **kwargs):
        super(LoanRequestForm, self).__init__(*args, **kwargs)
        self.fields['member'].queryset = CooperativeMember.objects.none()
        if self.instance.pk:
            cooperative = self.instance.member.id
            mbs = CooperativeMember.objects.filter(pk=cooperative)
            self.fields['member'].queryset = mbs


class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanRepaymentTransaction
        exclude = ['create_date', 'update_date']

    def __init__(self, *args, **kwargs):
        super(LoanRepaymentForm, self).__init__(*args, **kwargs)



bootstrapify(LoanRepaymentForm)
bootstrapify(LoanRequestForm)
bootstrapify(ApproveForm)
bootstrapify(LoanSearchForm)
bootstrapify(LoanUploadForm)
bootstrapify(CreditManagerForm)
bootstrapify(CreditManagerUserForm)
