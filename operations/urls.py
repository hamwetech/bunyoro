from django.conf.urls import url
from views.purchase import *

urlpatterns = [
    url('^purchase/list/', PurchaseListView.as_view(), name='purchase_list'),
    url('^purchase', PurchaseCreateView.as_view(), name='purchase')
    
 ]