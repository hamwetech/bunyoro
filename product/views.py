# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.forms.formsets import formset_factory, BaseFormSet
from django.shortcuts import render, redirect
from django.views.generic import View, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db import transaction

from conf.utils import log_debug, log_error
from product.models import *
from product.forms import *

class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)
        context['active'] = ['_union_prod']
        context['title'] = 'Country'
        context.update(self.extra_context)
        return context
    

class ProductUnitListView(ExtraContext, ListView):
    model = ProductUnit
    
    def get_context_data(self, **kwargs):
        context = super(ProductUnitListView, self).get_context_data(**kwargs)
        context['active'].append('__unit')
        return context
    
    

class ProductUnitCreateView(ExtraContext, CreateView):
    model = ProductUnit
    form_class = ProductUnitForm
    template_name = "product/productunit_form.html"
    success_url = reverse_lazy('product:unit_list')
    # 
    # def form_valid(self, form):
    #     form.instance.created_by = self.request.user
    #     return super(ProductCreateView, self).form_valid(form)
    def get_context_data(self, **kwargs):
        context = super(ProductUnitCreateView, self).get_context_data(**kwargs)
        context['active'].append('__unit')
        return context
    

class ProductUnitUpdateView(ExtraContext, UpdateView):
    model = ProductUnit
    form_class = ProductUnitForm
    template_name = "product/productunit_form.html"
    success_url = reverse_lazy('product:unit_list')
    # 
    # def form_valid(self, form):
    #     form.instance.created_by = self.request.user
    #     return super(ProductUpdateView, self).form_valid(form)
    def get_context_data(self, **kwargs):
        context = super(ProductUnitUpdateView, self).get_context_data(**kwargs)
        context['active'].append('__unit')
        return context
    
    
class ProductVariationListView(ExtraContext, ListView):
    model = Product
    template_name = "product/productvariation_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(ProductVariationListView, self).get_context_data(**kwargs)
        context['active'].append('__product')
        return context
    
    
class ProductVariationView(View):
    template_name = "product/product_variation_form.html"
    
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
        try:
            if pk:
                extra = 0
                prod = Product.objects.get(pk=pk)
                pvars = ProductVariation.objects.filter(product=prod)
                initial = [{'name': x.name, 'unit': x.unit} for x in pvars]
        except Exception as e:
            log_error()
            return redirect('product:variation_list')
        product_form = ProductForm(instance=prod)
        variation_form = formset_factory(ProductVariationForm, formset=BaseFormSet, extra=extra)
        variation_formset = variation_form(prefix='variation', initial=initial)
        data = {'form': product_form,
                'variation_formset': variation_formset,
                'active': ['_union_prod', '__product']}
        return render(request, self.template_name, data)
    
    def post(self, request, *args, **kwargs ):
        pk = self.kwargs.get('pk')
        prod = None
        var = None
        initial = None
        extra=1
        try:
            if pk:
                extra=1
                prod = Product.objects.get(pk=pk)
                pvars = ProductVariation.objects.filter(product=prod)
                initial = [{'name': x.name, 'unit': x.unit} for x in pvars]
        except Exception as e:
            log_error()
            return redirect('product:variation_list')
        product_form = ProductForm(request.POST, instance=prod)
        variation_form = formset_factory(ProductVariationForm, formset=BaseFormSet, extra=extra)
        variation_formset = variation_form(request.POST, prefix='variation')
        if product_form.is_valid() and variation_formset.is_valid():
            try:
                with transaction.atomic():
                    p = product_form.save(commit=False)
                    p.created_by = request.user
                    p.save()
                    if pk:
                        ProductVariation.objects.filter(product=p).delete()
                    for variation_form in variation_formset:
                        v = variation_form.save(commit=False)
                        v.product = p
                        v.created_by = request.user
                        v.save()
                return redirect('product:variation_list')
            except Exception as e:
                log_error()
        data = {'form': product_form,
                'variation_formset': variation_formset,
                'active': ['_union_prod', '__product']}
        return render(request, self.template_name, data)

# Variation Price
class ProductVariationPriceCreateView(ExtraContext, CreateView):
    model = ProductVariationPrice
    form_class = ProductVariationPriceForm
    template_name = "product/productvariationprice_form.html"
    success_url = reverse_lazy('product:price_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(ProductVariationPriceCreateView, self).form_valid(form)
    
    
    def get_context_data(self, **kwargs):
        context = super(ProductVariationPriceCreateView, self).get_context_data(**kwargs)
        context['active'].append('__price')
        return context
    

class ProductVariationPriceUpdateView(ExtraContext, UpdateView):
    model = ProductVariationPrice
    form_class = ProductVariationPriceForm
    template_name = "product/productvariationprice_form.html"
    success_url = reverse_lazy('product:price_list')
    # 
    # def form_valid(self, form):
    #     form.instance.created_by = self.request.user
    #     return super(ProductUpdateView, self).form_valid(form)
    def get_context_data(self, **kwargs):
        context = super(ProductVariationPriceUpdateView, self).get_context_data(**kwargs)
        context['active'].append('__price')
        return context
    
    
class ProductVariationPriceListView(ExtraContext, ListView):
    model = ProductVariationPrice
    template_name = "product/productvariationprice_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(ProductVariationPriceListView, self).get_context_data(**kwargs)
        context['active'].append('__price')
        return context
    

class ProductVariationPriceLogListView(ExtraContext, ListView):
    model =  ProductVariationPriceLog
    ordering = '-create_date'
    template_name = "product/productvariationpricelog_list.html"
    
    def get_queryset(self):
        qs = super(ProductVariationPriceLogListView, self).get_queryset()
        if self.kwargs.get('pk'):
            qs = qs.filter(product__pk=self.kwargs.get('pk'))
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(ProductVariationPriceLogListView, self).get_context_data(**kwargs)
        context['active'].append('__price')
        return context
    
def get_product_price(request, pk):
    try:
        pp = ProductVariationPrice.objects.get(product=pk)
        return JsonResponse({"price": pp.price})
    except Exception:
        return JsonResponse({"price": "error"})
   
    
class SupplierCreateView(ExtraContext, CreateView):
    model = Supplier
    form_class = SupplierForm
    extra_context = {'active': ['_union_prod','__supplier']}
    success_url = reverse_lazy('product:supplier_list')
    
    
class SupplierUpdateView(ExtraContext, UpdateView):
    model = Supplier
    form_class = SupplierForm
    extra_context = {'active': ['_union_prod','__supplier']}
    success_url = reverse_lazy('product:supplier_list')
    
    
class SupplierListView(ExtraContext, ListView):
    model = Supplier
    extra_context = {'active': ['_union_prod','__supplier']}
    

class ItemCreateView(ExtraContext, CreateView):
    model = Item
    form_class = ItemForm
    extra_context = {'active': ['_union_prod','__Item']}
    success_url = reverse_lazy('product:item_list')
    
    
class ItemUpdateView(ExtraContext, UpdateView):
    model = Item
    form_class = ItemForm
    extra_context = {'active': ['_union_prod','__Item']}
    success_url = reverse_lazy('product:item_list')
    
    
class ItemListView(ExtraContext, ListView):
    model = Item
    extra_context = {'active': ['_union_prod','__Item']}
    

def get_item_price(request, pk):
    try:
        pp = Item.objects.get(pk=pk)
        return JsonResponse({"price": pp.price})
    except Exception:
        return JsonResponse({"price": "error"})


class CategoryCreateView(ExtraContext, CreateView):
    model = Category
    form_class = CategoryForm
    extra_context = {'active': ['_category', '__Item']}
    success_url = reverse_lazy('product:category_list')


class CategoryUpdateView(ExtraContext, UpdateView):
    model = Category
    form_class = CategoryForm
    extra_context = {'active': ['_category', '__Item']}
    success_url = reverse_lazy('product:category_list')


class CategoryListView(ExtraContext, ListView):
    model = Category
    extra_context = {'active': ['_category', '__Item']}
