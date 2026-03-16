from django.conf.urls import url

from payment.views import *

urlpatterns = [
    
    url(r'bulk/delete/(?P<pk>[\w]+)/$', BulkPaymentDelete.as_view(), name='bulk_delete'),
    url(r'bulk/confirm/(?P<pk>[\w]+)/$', BulkPaymentConfirm.as_view(), name='bulk_confirm'),
    url(r'bulk/detail/(?P<pk>[\w]+)/$', BulkPaymentDetail.as_view(), name='bulk_detail'),
    url(r'bulk/list/$', BulkPaymentListView.as_view(), name='bulk_list'),
    url(r'bulk/upload/$', BulkPaymentView.as_view(), name='upload'),
    url(r'edit/(?P<pk>[\w]+)/$', PaymentMethodUpateView.as_view(), name='update'),
    url(r'detail/(?P<pk>[\w]+)/$', PaymentTransactionDetail.as_view(), name='detail'),
    url(r'dowload/$', DownloadPaymentExcelView.as_view(), name='download'),
    url(r'list/$', PaymentMethodListView.as_view(), name='list'),
    url(r'create/$', PaymentTransactionCreateView.as_view(), name='create')
]

