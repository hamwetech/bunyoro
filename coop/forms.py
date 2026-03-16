import xlrd
from django.utils import timezone
from django import forms
from os.path import splitext
from django.core.exceptions import NON_FIELD_ERRORS
from django.forms.formsets import formset_factory, BaseFormSet

from conf.utils import bootstrapify, internationalize_number, PHONE_REGEX
from coop.models import *
from conf.models import District, SubCounty, Village, Parish, PaymentMethod
from product.models import ProductVariation
from userprofile.models import Profile, Device, AssignedCards

class ClanForm(forms.ModelForm):
    class Meta:
        model = Clan
        fields = '__all__'


class CooperativeForm(forms.ModelForm):
    class Meta:
        model = Cooperative
        fields = ['name', 'fpo_type', 'logo', 'district', 'sub_county', 'phone_number', 'address', 'contact_person_name',
                  'product', 'is_active', 'send_message', 'sms_api_url', 'sms_api_token', 'payments_account',
                  'payments_token', 'payments_authentication', 'system_url', 'coop_abbreviation']
    
    def clean(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            try:
                phone_number = internationalize_number(phone_number)
                self.cleaned_data['phone_number'] = phone_number
            except ValueError:
                raise forms.ValidationError("Please enter a valid phone number.'%s' is not valid" % phone_number)
        return self.cleaned_data
        

class CooperativeUploadForm(forms.Form):
    
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

    
    excel_file = forms.FileField()
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class':'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class':'form-control'}))
    cooperative_col = forms.ChoiceField(label='Cooperative Column', initial=0, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Cooperative')
    district_col = forms.ChoiceField(label='District Column', initial=1, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the District')
    sub_county_col = forms.ChoiceField(label='Sub County Column', initial=2, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Sub County')
    contact_person = forms.ChoiceField(label='Contact Person Column', initial=3, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text="The column contains the Name of the Contact Person")
    phone_number = forms.ChoiceField(label='Phone Number Column', initial=4, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text="The column contains the Phone Number of Cooperative")
    
    
    def clean(self):
        data = self.cleaned_data
        f = data.get('excel_file', None)
        ext = splitext(f.name)[1][1:].lower()
        if not ext in ["xlsx", "xls"]:
            raise forms.ValidationError(("the File type is not accepted"))
        return data
            

class CooperativeSharePriceForm(forms.ModelForm):
    class Meta:
        model = CooperativeSharePrice
        exclude = ['created_by', 'create_date', 'update_date']
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(CooperativeSharePriceForm, self).__init__(*args, **kwargs)
        if not self.request.user.profile.is_union():
            self.fields['cooperative'].widget=forms.HiddenInput()
            self.fields['cooperative'].initial=self.request.user.cooperative_admin.cooperative


class CooperativeRegistrationFeeForm(forms.ModelForm):
    class Meta:
        model = CooperativeRegistrationFee
        exclude = ['created_by', 'create_date', 'update_date']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(CooperativeRegistrationFeeForm, self).__init__(*args, **kwargs)
        if not self.request.user.profile.is_union():
            self.fields['cooperative'].widget = forms.HiddenInput()
            self.fields['cooperative'].initial = self.request.user.cooperative_admin.cooperative
        

class AnimalIdentificationForm(forms.ModelForm):
    class Meta:
        model = AnimalIdentification
        exclude = ['create_date', 'update_date']


class TickControlForm(forms.ModelForm):
    class Meta:
        model = TickControl
        exclude = ['create_date', 'update_date']
    

class MemberProfileForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(MemberProfileForm, self).__init__(*args, **kwargs)
        
        self.fields['parish'].queryset = Parish.objects.none()
        
        if 'sub_county' in self.data:
            try:
                sub_county_id = int(self.data.get('sub_county'))
                self.fields['parish'].queryset = Parish.objects.filter(sub_county=sub_county_id).order_by('name')
            except Exception as e: #(ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            if self.instance.sub_county:
                self.fields['parish'].queryset = self.instance.sub_county.parish_set.order_by('name')
            
        if not self.request.user.profile.is_union():
            self.fields['cooperative'].widget=forms.HiddenInput()
            self.fields['cooperative'].initial=self.request.user.cooperative_admin.cooperative
            
    class Meta:
        model = CooperativeMember
        exclude = ['created_by', 'create_date',
                   'update_date', 'member_id', 'create_by', 'collection_amount',
                   'collection_quantity', 'savings_balance', 'paid_amount']
    
    def clean(self):
        phone_number = self.cleaned_data.get('phone_number')
        other_phone_number = self.cleaned_data.get('other_phone_number')
        
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            if date_of_birth > timezone.now().date():
                raise forms.ValidationError("Error! Date of Birth cannot be in the Future")
        
        if phone_number:
            try:
                phone_number = internationalize_number(phone_number)
                self.cleaned_data['phone_number'] = phone_number
            except ValueError:
                raise forms.ValidationError("Please enter a valid phone number.'%s' is not valid" % phone_number)
        if other_phone_number:
            try:
                other_phone_number = internationalize_number(other_phone_number)
                self.cleaned_data['other_phone_number'] = other_phone_number
            except ValueError:
                raise forms.ValidationError("Please enter a valid phone number.'%s' is not valid" % other_phone_number)
        return self.cleaned_data


class MemberProfileSearchForm(forms.Form):
    choices=(('', 'Role'), ('Chairman', 'Chairman'), ('Vice Chairman', 'Vice Chairman'), ('Treasurer', 'Treasurer'),
        ('Secretary', 'Secretary'), ('Member', 'Member'),('Secretary Manager', 'Secretary Manager'), ('Patron', 'Patron'))
        
    card_number = forms.CharField(max_length=150, required=False)
    name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=150, required=False)
    # cooperative = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    role = forms.ChoiceField(widget=forms.Select(), choices=choices, required=False)
    district = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    create_by = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self,  *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super (MemberProfileSearchForm, self).__init__(*args, **kwargs)
       
        # qs = CooperativeMember.objects.values('cooperative__id', 'cooperative__name').distinct()
        d_qs = CooperativeMember.objects.values('district__id', 'district__name').distinct()
        # choices = [['', 'Cooperative']]
        dchoices = [['', 'District']]
        # for q in qs:
        #     choices.append([q['cooperative__id'], q['cooperative__name']])
        
        for dq in d_qs:
            dchoices.append([dq['district__id'], dq['district__name']])

        self.fields['create_by'].queryset = Profile.objects.all()
        # self.fields['cooperative'].choices = choices
        self.fields['district'].choices = dchoices
        if not self.request.user.profile.is_union():
            # self.fields.pop('cooperative')
            self.fields.pop('create_by')


class MemberUploadForm(forms.Form):
    
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
    
    excel_file = forms.FileField()
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class':'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class':'form-control'}))
    farmer_name_col = forms.ChoiceField(label='Farmer Name Column', initial=0, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Farmers Name')
    identification_col = forms.ChoiceField(label='Identification Number', initial=1, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Countries Identification Number of the Member')
    gender = forms.ChoiceField(label='Gender Column', initial=2, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Gender')
    date_of_birth_col = forms.ChoiceField(label='Date of Birth Column', initial=3, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Date of birth')
    phone_number_col = forms.ChoiceField(label='Phone Number Column', initial=4, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Phone Number')
    role_col = forms.ChoiceField(label='Role Column', initial=5, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Cooperate Role')
    acreage_col = forms.ChoiceField(label='Acreage Column', initial=6, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Cotton Acreage')
    # soya_col = forms.ChoiceField(label='Soya Acreage Column', initial=6, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Soya Acreage')
    # soghum_col = forms.ChoiceField(label='Soghum Acreage Column', initial=7, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Soghum Acreage')
    cooperative_col = forms.ChoiceField(label='Cooperative Column', initial=7, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Cooperative')
    district_col = forms.ChoiceField(label='Distric Column', initial=8, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the District')
    county_col = forms.ChoiceField(label='County Column', initial=9, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the County')
    sub_county_col = forms.ChoiceField(label='Sub County Column', initial=10, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Sub county')
    parish_col = forms.ChoiceField(label='Parish Column', initial=11, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Parish')
    village_col = forms.ChoiceField(label='Village Column', initial=12, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Village')
    # organisation_col = forms.ChoiceField(label='Organisation Column', initial=14, choices=choices, widget=forms.Select(attrs={'class':'form-control'}), help_text='The column containing the Organisation')
    
    
    def clean(self):
        data = self.cleaned_data
        f = data.get('excel_file', None)
        ext = splitext(f.name)[1][1:].lower()
        if not ext in ["xlsx", "xls"]:
            raise forms.ValidationError(("The File type is not accepted"))
        return data


class CooperativeMemberBusinessForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberBusiness
        exclude = ['create_date', 'update_date']
        
        widgets = {
          'other_animal_diseases': forms.Textarea(attrs={'rows':1}),
        }


class CooperativeMemberProductDefinitionForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberProductDefinition
        exclude = ['create_date', 'update_date']
        
        widgets = {
          'product_variation': forms.CheckboxSelectMultiple(),
        }
        

class CooperativeMemberProductQuantityForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberProductQuantity
        exclude = ['create_date', 'update_date']


class DewormingScheduleForm(forms.ModelForm):
    class Meta:
        model = DewormingSchedule
        exclude = ['create_date', 'update_date']
        
        
class CooperativeMemberHerdMaleForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberHerdMale
        exclude = ['create_date', 'update_date']
        

class CooperativeMemberHerdFemaleForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberHerdFemale
        exclude = ['create_date', 'update_date']
    
 
class CooperativeMemberProductForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberProduct
        exclude = ['create_date', 'update_date']
  
        
class CooperativeMemberSupplyForm(forms.ModelForm):
    
    choices = (
            ('January', 'January'),
            ('February', 'February'),
            ('March', 'March'),
            ('April', 'April'),
            ('May', 'May'),
            ('June', 'June'),
            ('July', 'July'),
            ('August', 'August'),
            ('September', 'September'),
            ('October', 'October'),
            ('November', 'November'),
            ('December', 'December'),
        )
    # probable_sell_month = forms.MultipleChoiceField(widget=forms.SelectMultiple,
                                             # choices=choices)
    class Meta:
        model = CooperativeMemberSupply
        exclude = ['create_date', 'update_date']
    
    def __init__(self, *args, **kwargs):
        super(CooperativeMemberSupplyForm, self).__init__(*args, **kwargs)
        self.fields['probable_sell_month'] = forms.MultipleChoiceField(widget=forms.SelectMultiple, choices=self.choices, required=False)
        if self.instance.probable_sell_month:
            self.initial['probable_sell_month'] = eval(self.instance.probable_sell_month)


class CommonDiseasesForm(forms.ModelForm):
    class Meta:
        model = CommonDisease
        exclude = ['create_date', 'update_date']


class DownloadMemberOptionForm(forms.Form):
    profile = forms.BooleanField(initial=True)
    farm = forms.BooleanField(required=False)
    herd = forms.BooleanField(required=False)
    member_supply = forms.BooleanField(required=False)
    
     
class DeprecatedDownloadMemberOptionForm(forms.Form):
    profile_choices = [['cooperative', 'Cooperative'], ['member_id', 'Memeber Id'], ['surname', 'Surname'], ['other_name', 'Other Name'],['date_of_birth', 'date_of_birth'],['gender', 'gender'],['maritual_status', 'maritual_status'],
        ['phone_number', 'phone_number'],['email', 'email'],['district', 'district'],['sub_county', 'sub_county'],['village', 'village'],['address', 'address'],
        ['gps_coodinates', 'gps_coodinates'],['children', 'children'],['other_household_members', 'other_household_members'],['education_level', 'education_level'],
        ['primary_income_source', 'primary_income_source'],['membership_fee', 'membership_fee'],
        ['coop_role', 'coop_role'],['animal_count', 'animal_count'],['shares', 'shares'],['sale_amount', 'sale_amount'],['paid_amount', 'paid_amount'],['surname', 'surname'],]
    
    farm_choices = [['business_name','business_name'], ['farm_district','farm_district'],['farm_sub_county','farm_sub_county'],['gps_coodinates','gps_coodinates'],
        ['size','size'],['fenced','fenced'],['paddock','paddock'],['water_source','water_source'],
        ['animal_identification','animal_identification'],['common_diseases','common_diseases'],['other_animal_diseases','other_animal_diseases'],['tick_control','tick_control']]
    
    deworming = [['deworm_date', 'deworm_date'], ['dewormer', 'dewormer']]
    
    breed = [['product_variation', 'Breed']]
    
    male_herd = [['adults', 'adults'], ['bullocks', 'bullocks'], ['calves', 'calves']]
    female_herd = [['f_adults', 'f_adults'], ['bullocks', 'bullocks'], ['f_calves', 'f_calves']]
    member_supply = [['nearest_market', 'nearest_market'], ['product_average_cost', 'product_average_cost'], ['price_per_kilo', 'price_per_kilo'],
        ['probable_sell_month', 'probable_sell_month'], ['sell_to_cooperative_society', 'sell_to_cooperative_society']]
    
    profile = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=profile_choices)
    farm = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=farm_choices)
    deworming = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=deworming)
    breed = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=breed)
    bull_herd = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=male_herd)
    cow_herd = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=female_herd)
    member_supply = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=member_supply)
    
        
class CooperativeContributionForm(forms.ModelForm):
    class Meta:
        model = CooperativeContribution
        exclude = ['create_date', 'update_date']
        

class CooperativeShareTransactionForm(forms.ModelForm):
       
    class Meta:
        model = CooperativeShareTransaction
        exclude = ['create_date', 'update_date'] 
    

class MemberSubscriptionForm(forms.ModelForm):
    class Meta:
        model = CooperativeMemberSubscriptionLog
        exclude = ['create_date', 'update_date']
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Member is Subscribed for the Year provided",
            }
        }

#
class RegistrationTransactionForm(forms.Form):
    cooperative = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    member = forms.ModelChoiceField(queryset=CooperativeMember.objects.all())
    amount = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': True}))
    phone_number = forms.IntegerField()

    # class Meta:
    #     model = RegistrationTransaction
    #     exclude = ['create_date', 'update_date']
    #
    #     widgets = {
    #         'price': forms.TextInput(attrs={'readonly': True}),
    #     }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(RegistrationTransactionForm, self).__init__(*args, **kwargs)

        qs = Cooperative.objects.all()

        choices = [['', 'Cooperative']]

        for q in qs:
            choices.append([q.id, q.name])

        self.fields['cooperative'].choices = choices
        self.fields['member'].queryset = CooperativeMember.objects.none()

        if 'cooperative' in self.data:

            try:
                cooperative_id = int(self.data.get('cooperative'))
                self.fields['member'].queryset = CooperativeMember.objects.filter(
                    cooperative=cooperative_id).order_by('first_name')
            except Exception as e:  # (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
                self.fields['member'].queryset = CooperativeMember.objects.none()

        # elif self.instance.pk:
        #
        #     if self.instance.cooperative:
        #         self.fields['member'].queryset = self.instance.cooperative.member_set.order_by('first_name')
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            price = CooperativeRegistrationFee.objects.filter(
                cooperative=cooperative).order_by('-create_date')
            self.fields['amount'].initial = price[0].price if price else ""
            self.fields['member'].queryset = self.fields['member'].queryset.filter(
                cooperative=cooperative)
#
      
        
class MemberSharesForm(forms.ModelForm):
    cooperative = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    class Meta:
        model = CooperativeMemberSharesLog
        exclude = ['create_date', 'update_date']
        
        widgets = {
          'shares': forms.TextInput(attrs={'readonly': True}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(MemberSharesForm, self).__init__(*args, **kwargs)
        
        qs = Cooperative.objects.all()
        
        choices = [['', 'Cooperative']]
        
        for q in qs:
            choices.append([q.id, q.name])
        
        self.fields['cooperative'].choices = choices
        
        self.fields['cooperative_member'].queryset = CooperativeMember.objects.none()
        
        
            
        if 'cooperative' in self.data:
            
            try:
                
                cooperative_id = int(self.data.get('cooperative'))
                self.fields['cooperative_member'].queryset = CooperativeMember.objects.filter(cooperative=cooperative_id).order_by('first_name')
            except Exception as e: #(ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
               
                self.fields['cooperative_member'].queryset = CooperativeMember.objects.none()
                
        elif self.instance.pk:
            
            if self.instance.cooperative:
                self.fields['cooperative_member'].queryset = self.instance.cooperative.member_set.order_by('first_name')
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            price = CooperativeSharePrice.objects.filter(
                cooperative=cooperative).order_by('-create_date')
            self.fields['shares_price'].initial=price[0].price if price else ""
            self.fields['cooperative_member'].queryset = self.fields['cooperative_member'].queryset.filter(cooperative=cooperative)
        

class MemberSupplyRequestConfirmForm(forms.ModelForm):
    class Meta:
        model = MemberSupplyRequest
        fields = ('status', 'confirmed_by', 'comfirmation_method', 'remark')
    
    # def __init__(self, *args, **kwargs):
    #     self.request = kwargs.pop('request', None)
    #     super(MemberSupplyRequestConfirmForm, self).__init__(*args, **kwargs)
    #     if not self.request.user.profile.is_union():
    #         cooperative = self.request.user.cooperative_admin.cooperative
    #         self.fields['cooperative_member'].queryset = self.fields['cooperative_member'].queryset.filter(cooperative=cooperative)
    #    


class MemberSupplyRequestForm(forms.ModelForm):
    class Meta:
        model = MemberSupplyRequest
        exclude = ('create_date', 'update_date', 'transaction_reference', 'created_by')
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(MemberSupplyRequestForm, self).__init__(*args, **kwargs)
        if not self.request.user.profile.is_union():
            cooperative = self.request.user.cooperative_admin.cooperative
            self.fields['cooperative_member'].queryset = self.fields['cooperative_member'].queryset.filter(cooperative=cooperative)
    
    def clean(self):
        data = self.cleaned_data
        trx_date = data.get('supply_date')
        if trx_date < timezone.now().date():
                raise forms.ValidationError("Error! The Supply date cannot be in the Past")
        return data
    

class VariationSupplyRequestFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return

        breeds = []
        duplicates = False
        
        
        for form in self.forms:
            if form.cleaned_data:
                breed = form.cleaned_data['breed']
                
                # Check that no two links have the same anchor or URL
                if breed:
                    if breed in breeds:
                        duplicates = True
                    breeds.append(breed)
                
                if duplicates:
                    raise forms.ValidationError(
                        'Duplicate Breeds Found',
                        code='duplicate_values'
                    )
        

class MemberSupplyRequestVariationForm(forms.ModelForm):
    class Meta:
        model = MemberSupplyRequestVariation
        exclude = ('create_date', 'update_date', 'created_by')
  
     
class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        exclude = ['create_date', 'update_date']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(CollectionForm, self).__init__(*args, **kwargs)
        self.fields['collection_date'].widget=forms.TextInput(attrs={"data-uk-datepicker": "{maxDate:10, format:'YYYY-MM-D'}"})

        
        if not self.request.user.profile.is_union():
            self.fields['cooperative'].widget=forms.HiddenInput()
            self.fields['cooperative'].initial=self.request.user.cooperative_admin.cooperative
        
    def clean(self):
        data = self.cleaned_data
        member = data.get('member')
        name = data.get('name')
        phone_number = data.get('phone_number')
        if not member:
            if not name and not phone_number:
                raise forms.ValidationError("Error! Please Select a Member or provide the Name of a non-member")
        if phone_number:       
            try:
                phone_number = internationalize_number(phone_number)
                self.cleaned_data['phone_number'] = phone_number
            except ValueError:
                raise forms.ValidationError("Please enter a valid phone number.'%s' is not valid" % phone_number)
        
        return data
    
    
class CollectionFilterForm(forms.Form):
    search = forms.CharField(max_length=160, required=False)
    cooperative = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    product = forms.ChoiceField(widget=forms.Select(), required=False)
    start_date = forms.CharField(max_length=160, required=False, widget=forms.TextInput(attrs={"data-uk-datepicker":"{format:'YYYY-MM-DD'}"}))
    end_date = forms.CharField(max_length=160, required=False, widget=forms.TextInput(attrs={"data-uk-datepicker":"{format:'YYYY-MM-DD'}"}))
    
    def __init__(self, *args, **kwargs):
        super(CollectionFilterForm, self).__init__(*args, **kwargs)
        choices = [['', '--------------']]
        choices.extend([[pv.id, pv.name]  for pv in ProductVariation.objects.all()])
        self.fields['product'].choices = choices
        choices = [['', 'Cooperative']]
        qs = Cooperative.objects.all()
        for q in qs:
            choices.append([q.id, q.name])
        self.fields['cooperative'].choices = choices


class MemberOrderForm(forms.ModelForm):
    class Meta:
        model = MemberOrder
        fields = ['cooperative', 'member', 'order_date']
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(MemberOrderForm, self).__init__(*args, **kwargs)
        
        if not self.request.user.profile.is_union():
            self.fields['cooperative'].widget=forms.HiddenInput()
            self.fields['cooperative'].initial=self.request.user.cooperative_admin.cooperative
        
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
    
        
class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        exclude = ['create_date', 'update_date', 'created_by', 'unit_price']
        widgets = {
          'item': forms.Select(attrs={'onChange': 'refreshInput(this)', 'class': 'id_item'}),
          'quantity': forms.TextInput(attrs={'onkeydown': 'calculatePrice(this)'}),
        }

class FarmerGroupForm(forms.ModelForm):
    class Meta:
        model = FarmerGroup
        fields = '__all__'


class SavingsForm(forms.ModelForm):
    class Meta:
        model = Savings
        exclude = ['created_by', 'reference', 'balance_after']


class OrderUploadForm(forms.Form):
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
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class': 'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class': 'form-control'}))
    farmer_reference_col = forms.ChoiceField(label='Farmer ID / Phone number Column', initial=0, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Farmers SYSTEM ID/Phone Number')
    farmer_name_col = forms.ChoiceField(label='Farmer Name Column', initial=1, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Farmers Name')
    item_col = forms.ChoiceField(label='Item Column', initial=2, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Item')
    quantity_col = forms.ChoiceField(label='Quantity Column', initial=3, choices=choices,
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 help_text='The column containing the Quantity')
    order_date_col = forms.ChoiceField(label='Order Date Column', initial=4, choices=choices,
                                     widget=forms.Select(attrs={'class': 'form-control'}),
                                     help_text='The column containing the Order Date')


class CollectionUploadForm(forms.Form):
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
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class': 'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class': 'form-control'}))
    farmer_reference_col = forms.ChoiceField(label='Farmer ID / Phone number Column', initial=0, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Farmers SYSTEM ID/Phone Number')
    farmer_name_col = forms.ChoiceField(label='Farmer Name Column', initial=1, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Farmers Name')
    product_col = forms.ChoiceField(label='Product Column', initial=2, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Product')
    quantity_col = forms.ChoiceField(label='Quantity Column', initial=3, choices=choices,
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 help_text='The column containing the Quantity')
    collection_date_col = forms.ChoiceField(label='Collection Date Column', initial=4, choices=choices,
                                     widget=forms.Select(attrs={'class': 'form-control'}),
                                     help_text='The column containing the Collection Date')



class AgentSearchForm(forms.Form):
    name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=150, required=False)
    farmer_group = forms.ChoiceField(widget=forms.Select(), choices=[], required=False)
    start_date = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class':'some_class', 'id':'uk_dp_1',
                                                                                               'data-uk-datepicker': "{format:'YYYY-MM-DD'}",
                                                                                               'autocomplete':"off"}))
    end_date = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class':'some_class', 'id':'uk_dp_1',
                                                                                               'data-uk-datepicker': "{format:'YYYY-MM-DD'}",
                                                                                               'autocomplete':"off"}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AgentSearchForm, self).__init__(*args, **kwargs)

        qs = CooperativeMember.objects.values('farmer_group__id', 'farmer_group__name').distinct()

        choices = [['', 'Farmer Groups']]
        for q in qs:
            choices.append([q['farmer_group__id'], q['farmer_group__name']])

        self.fields['farmer_group'].choices = choices


class AgentForm__(forms.ModelForm):
    district = forms.MultipleChoiceField(required=False, choices=[])
    farmer_group = forms.MultipleChoiceField(required=False, choices=[])
    confirm_password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    msisdn = forms.CharField(max_length=150)
    sex = forms.ChoiceField(widget=forms.Select(), choices=[['', '--------------'], ['Male', 'Male'], ['Female', 'Female']])
    date_of_birth = forms.CharField(max_length=150, required=False)
    nin = forms.CharField(max_length=150, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'sex', 'date_of_birth', 'msisdn', 'is_active', 'username', 'password',
                  'confirm_password']

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(AgentForm, self).__init__(*args, **kwargs)

        self.fields['farmer_group'].choices = [[x.id, x.name] for x in FarmerGroup.objects.all()]
        self.fields['district'].choices = [[x.id, x.name] for x in District.objects.all()]
        self.fields['farmer_group'].widget.attrs.update({'class': "selec_adv_1"})
        self.fields['district'].widget.attrs.update({'class': "selec_adv_1"})

        if instance:
            self.fields.pop('password')
            self.fields.pop('confirm_password')


class AgentForm(forms.ModelForm):
    password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    confirm_password = forms.CharField(max_length=150, required=True, widget=forms.PasswordInput)
    class Meta:
        model = User
        exclude = ['create_date', 'last_login', 'is_superuser', 'groups', 'user_permissions', 'date_joined', 'password']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super(AgentForm, self).__init__(*args, **kwargs)
        # self.fields['district_incharge'].widget.attrs.update({'class': "selec_adv_1"})
        if instance:
            self.fields.pop('password')
            self.fields.pop('confirm_password')

    def clean(self):
        cleaned_data = super(AgentForm, self).clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Validate that the passwords match for new user creation
        if not self.instance and password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['user', 'access_level', 'is_supervisor']

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['district_incharge'].widget.attrs.update({'class': "selec_adv_1"})


    def clean(self):
        if not self.cleaned_data.get('supervisor'):
            raise forms.ValidationError("Supervisor is required.")


class AgentUpdateForm(forms.ModelForm):
    district = forms.MultipleChoiceField(required=False, choices=[])
    farmer_group = forms.MultipleChoiceField(required=False, choices=[])
    msisdn = forms.CharField(max_length=150)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'msisdn', 'is_active', 'username']

    def __init__(self, *args, **kwargs):
        super(AgentUpdateForm, self).__init__(*args, **kwargs)
        self.fields['farmer_group'].choices = [[x.id, x.name] for x in FarmerGroup.objects.all()]
        self.fields['district'].choices = [[x.id, x.name] for x in District.objects.all()]
        self.fields['farmer_group'].widget.attrs.update({'class': "selec_adv_1"})
        self.fields['district'].widget.attrs.update({'class': "selec_adv_1"})


class AgentUploadForm(forms.Form):
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
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class': 'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class': 'form-control'}))
    name_col = forms.ChoiceField(label='Name Column', initial=0, choices=choices,
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        help_text='The column containing the Names')
    email_column = forms.ChoiceField(label='Email Column', initial=1, choices=choices,
                                     widget=forms.Select(attrs={'class': 'form-control'}),
                                     help_text='The column containing the email')
    phone_number_col = forms.ChoiceField(label='Phone Number Column', initial=2, choices=choices,
                                       widget=forms.Select(attrs={'class': 'form-control'}),
                                       help_text='The column containing the phone number')
    district_col = forms.ChoiceField(label='Distric Column', initial=3, choices=choices,
                                     widget=forms.Select(attrs={'class': 'form-control'}),
                                     help_text='The column containing the District')
    username_col = forms.ChoiceField(label='Password Column', initial=4, choices=choices,
                                       widget=forms.Select(attrs={'class': 'form-control'}),
                                       help_text='The column containing the username')
    password_col = forms.ChoiceField(label='Password Column', initial=5, choices=choices,
                                   widget=forms.Select(attrs={'class': 'form-control'}),
                                   help_text='The column containing the password')


    def clean(self):
        data = self.cleaned_data
        f = data.get('excel_file', None)
        ext = splitext(f.name)[1][1:].lower()
        if not ext in ["xlsx", "xls"]:
            raise forms.ValidationError(("the File type is not accepted"))
        return data


class AssignDeviceForm(forms.Form):
    device = forms.ChoiceField(widget=forms.Select(), choices=[])

    def __init__(self, *args, **kwargs):
        initial_data = kwargs.pop('initial', {})
        super(AssignDeviceForm, self).__init__(*args, **kwargs)
        choices = [['', '--------------']]
        choices.extend([[x.id, x.device_id] for x in Device.objects.all()])
        self.fields['device'].choices = choices
        self.fields['device'].widget.attrs.update({'class': "selec_adv_1"})
        self.fields['device'].initial = initial_data.get('device', None)
        self.initial['device'] = initial_data.get('device', None)


class AssignCardsForm(forms.Form):
    card_number  = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        initial_data = kwargs.pop('initial', {})
        super(AssignCardsForm, self).__init__(*args, **kwargs)
        self.initial['card_number'] = initial_data.get('number_of_cards', None)


class SeasonForm(forms.ModelForm):
    class Meta:
        model = Season
        exclude = ['created_by',]


class OKOLocationForm(forms.Form):
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
    sheet = forms.ChoiceField(label="Sheet", choices=sheetChoice, widget=forms.Select(attrs={'class': 'form-control'}))
    row = forms.ChoiceField(label="Row", choices=rowchoices, widget=forms.Select(attrs={'class': 'form-control'}))


bootstrapify(OKOLocationForm)
bootstrapify(SeasonForm)
bootstrapify(AssignCardsForm)
bootstrapify(AssignDeviceForm)
bootstrapify(SavingsForm)
bootstrapify(AgentUploadForm)
bootstrapify(AgentForm)
bootstrapify(ProfileForm)
bootstrapify(AgentUpdateForm)
bootstrapify(OrderUploadForm)
bootstrapify(CollectionUploadForm)
bootstrapify(FarmerGroupForm)
bootstrapify(MemberOrderForm)
bootstrapify(OrderItemForm)
bootstrapify(ClanForm)
bootstrapify(CooperativeForm)
bootstrapify(MemberUploadForm)
bootstrapify(CooperativeUploadForm)
bootstrapify(CooperativeSharePriceForm)
bootstrapify(MemberProfileForm)
bootstrapify(CooperativeMemberBusinessForm)
bootstrapify(CooperativeMemberProductForm)
bootstrapify(CooperativeMemberSupplyForm)
bootstrapify(CooperativeContributionForm)
bootstrapify(CooperativeShareTransactionForm)
bootstrapify(MemberSubscriptionForm)
bootstrapify(MemberSharesForm)
bootstrapify(CooperativeMemberProductDefinitionForm)
bootstrapify(CooperativeMemberProductQuantityForm)
bootstrapify(CooperativeMemberProductQuantityForm)
bootstrapify(MemberProfileSearchForm)
bootstrapify(CooperativeMemberHerdMaleForm)
bootstrapify(CooperativeMemberHerdFemaleForm)
bootstrapify(CommonDiseasesForm)
bootstrapify(DewormingScheduleForm)
bootstrapify(MemberSupplyRequestForm)
bootstrapify(MemberSupplyRequestConfirmForm)
bootstrapify(MemberSupplyRequestVariationForm)
bootstrapify(CollectionForm)
bootstrapify(CollectionFilterForm)
bootstrapify(CooperativeRegistrationFeeForm)
bootstrapify(CooperativeSharePriceForm)
bootstrapify(RegistrationTransactionForm)