from django.conf.urls import url

from account.views import *


urlpatterns = [
    url(r'transaction/list/$', TransactionListView.as_view(), name='transaction_list'),
]