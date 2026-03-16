from django.conf.urls import url

from credit.views import *

urlpatterns = [


      url(r'cm/list/(?P<cm>[\w]+)/$', CreditManagerAdminListView.as_view(), name="cm_admin_list"),
      url(r'cm/create/(?P<cm>[\w]+)/$', CreditManagerAdminCreateView.as_view(), name="cm_admin_create"),


      url(r'loan/list/$', LoanRequestListView.as_view(), name='loan_list'),
      url(r'loan/upload/$', LoanRequestUploadView.as_view(), name='loan_upload'),
      url(r'loan/repayment/logs/$', LoanRepaymentListView.as_view(), name='loan_repayment'),
      url(r'loan/(?P<pk>[\w]+)/$', LoanRequestDetailView.as_view(), name='loan_detail'),
      url(r'loan/repayment/(?P<pk>[\w]+)/$', LoanRepaymentFormView.as_view(), name='loan_repayment'),
      url(r'loan/edit/(?P<pk>[\w]+)/$', LoanRequestEdit.as_view(), name='loan_edit'),
      url(r'loan/delete/(?P<pk>[\w]+)/$', LoanRequestDeleteView.as_view(), name='loan_delete'),
      url(r'loan/approve/(?P<pk>[\w]+)/(?P<status>[\w]+)/$', ApproveLoan.as_view(), name='loan_approve'),

      url(r'loan/approval/(?P<pk>[\w]+)/$', ApproveLoanFormView.as_view(), name='approve_form'),

      url(r'loan/transaction/list/$', LoanTransactionListView.as_view(), name='loan_transaction_list'),

      url(r'list/$', CreditManagerListView.as_view(), name='cm_list'),
      url(r'create/$', CreditManagerCreateView.as_view(), name='cm_create'),
      url(r'edit/(?P<pk>[\w]+)/$', CreditManagerUpdateView.as_view(), name='cm_update'),

]