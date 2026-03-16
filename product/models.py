# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=25, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product'
    
    def product_variation(self):
        return ProductVariation.objects.filter(product=self)
    
    
    def __unicode__(self):
        return self.name
    

class ProductUnit(models.Model):
    name = models.CharField(max_length=25, unique=True)
    code = models.CharField(max_length=3, unique=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_units'
        verbose_name = 'Product Unit'
        verbose_name_plural = 'Product Units'
        
    
    def __unicode__(self):
        return self.name
    

class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    unit = models.ForeignKey(ProductUnit, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation'
        verbose_name = 'Product'
        verbose_name_plural = 'Product'
        unique_together = ['product', 'name']
           
    def __unicode__(self):
        return self.name

    def get_price(self):
        try:
            prod = ProductVariationPrice.objects.get(product=self)
            return prod.price
        except Exception as e:
            return 0
    

class ProductVariationPrice(models.Model):
    product = models.ForeignKey(ProductVariation, related_name='variation_price', on_delete=models.CASCADE)
    unit = models.ForeignKey(ProductUnit, null=True, blank=True, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation_price'
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'
        unique_together = ['product', 'unit']
        
    def __unicode__(self):
        return "%s" % self.product


class ProductVariationPriceLog(models.Model):
    product = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    unit = models.ForeignKey(ProductUnit, null=True, blank=True, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variation_price_log'
        verbose_name = 'Product Price'
        verbose_name_plural = 'Product Prices'
        
    def __unicode__(self):
        return "%s" % self.product
    
class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'supplier'
        
    def __unicode__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category'

    def __unicode__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    unit = models.ForeignKey(ProductUnit, null=True, blank=True, on_delete=models.SET_NULL)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'item'
        
    def __unicode__(self):
        return self.name
    
# @receiver(post_save, sender=ProductVariationPrice)
# def create_price_log(sender, instance, created, **kwargs):
#     if created:
#         ProductVariationPriceLog.objects.create(variation=instance)

@receiver(post_save, sender=ProductVariationPrice)
def save_price_log(sender, instance, **kwargs):
    ProductVariationPriceLog.objects.create(product=instance.product,
                                            price=instance.price,
                                            unit=instance.unit,
                                            created_by=instance.created_by) 
