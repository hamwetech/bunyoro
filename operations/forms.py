from django import forms

from conf.utils import bootstrapify
from django.forms.formsets import BaseFormSet
from operations.models import Purchase, PurchaseProduct


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        exclude = ['create_date', 'update_date']
    
    

class PurchaseProductForm(forms.ModelForm):
    
    # def __init__(self, *args, **kwargs):
    #     super(PurchaseProductForm, self).__init__(*args, **kwargs)
    #     self.fields['breed'].widget.attrs['onchange'] = 'get_price()'
        
    class Meta:
        model = PurchaseProduct
        exclude = ['create_date', 'update_date']
        
        
class PurchasePrefixFormSet(BaseFormSet):
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
                        prefixs.append(breed)

                if duplicates:
                    raise forms.ValidationError(
                        'Duplicate Values Found',
                        code='duplicate_values'
                    )
    
bootstrapify(PurchaseForm)
bootstrapify(PurchaseProductForm)