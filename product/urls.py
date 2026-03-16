from django.conf.urls import url

from product.views import *

urlpatterns = [
      url(r'item/price/(?P<pk>[\w]+)/$', get_item_price, name='item_price'),
      url(r'item/edit/(?P<pk>[\w]+)/$', ItemUpdateView.as_view(), name='item_update'),
      url(r'item/list/$', ItemListView.as_view(), name='item_list'),
      url(r'item/create/$', ItemCreateView.as_view(), name='item_create'),
      url(r'supplier/edit/(?P<pk>[\w]+)/$', SupplierUpdateView.as_view(), name='supplier_update'),
      url(r'supplier/list/$', SupplierListView.as_view(), name='supplier_list'),
      url(r'supplier/create/$', SupplierCreateView.as_view(), name='supplier_create'),
         
      url(r'price/log/(?P<pk>[\w]+)/$', ProductVariationPriceLogListView.as_view(), name='price_log_list'),
      url(r'price/request/(?P<pk>[\w]+)/$', get_product_price, name='product_price'),
      url(r'price/list/$', ProductVariationPriceListView.as_view(), name='price_list'),
      url(r'price/create/$', ProductVariationPriceCreateView.as_view(), name='price_create'),
      url(r'price/(?P<pk>[\w]+)/$', ProductVariationPriceUpdateView.as_view(), name='price_edit'),
      url(r'variation/list/$', ProductVariationListView.as_view(), name='variation_list'),
      url(r'variation/create/$', ProductVariationView.as_view(), name='variation_create'),
      url(r'variation/(?P<pk>[\w]+)/$', ProductVariationView.as_view(), name='variation_edit'),
      url(r'unit/list/$', ProductUnitListView.as_view(), name='unit_list'),
      url(r'unit/create/$', ProductUnitCreateView.as_view(), name='unit_create'),
      url(r'unit/(?P<pk>[\w]+)/$', ProductUnitUpdateView.as_view(), name='unit_edit'),

      url(r'category/list/$', CategoryListView.as_view(), name='category_list'),
      url(r'category/create/$', CategoryCreateView.as_view(), name='category_create'),
      url(r'category/(?P<pk>[\w]+)/$', CategoryUpdateView.as_view(), name='category_update'),
]