from django import forms

from conf.utils import bootstrapify
from product.models import *

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class ProductUnitForm(forms.ModelForm):
    class Meta:
        model = ProductUnit
        fields = ['name', 'code']
        
        
class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['name', 'unit']


class ProductVariationPriceForm(forms.ModelForm):
    class Meta:
        model = ProductVariationPrice
        fields = ['product', 'unit', 'price']
        
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name']
        
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        exclude = ['create_date', 'update_date']
    
       
bootstrapify(SupplierForm)
bootstrapify(ItemForm)
bootstrapify(ProductForm)
bootstrapify(ProductUnitForm)
bootstrapify(ProductVariationForm)
bootstrapify(ProductVariationPriceForm)
