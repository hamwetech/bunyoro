from django.conf.urls import url

from coop.views.cooperative import *
from coop.views.member import *
from coop.views.collection import *
from coop.views.order import *
from coop.views.agent import *
from coop.views.savings import *

urlpatterns = [
    
     url(r'order/status/(?P<pk>[\w]+)/(?P<status>[\w]+)$', MemberOrderStatusView.as_view(), name='order_status'),
     
     url(r'order/delete/(?P<pk>[\w]+)/$', MemberOrderDeleteView.as_view(), name='order_delete'),
     url(r'order/detail/(?P<pk>[\w]+)/$', MemberOrderDetailView.as_view(), name='order_detail'),
     url(r'order/create/(?P<pk>[\w]+)/$', MemberOrderCreateView.as_view(), name='order_update'),
     url(r'order/create/$', MemberOrderCreateView.as_view(), name='order_create'),
     url(r'order/list/$', MemberOrderListView.as_view(), name='order_list'),
     url(r'order/upload/$', OrderUploadView.as_view(), name='order_upload'),

     url(r'savings/list/$', SavingsListView.as_view(), name='savings_list'),
     url(r'savings/create/$', SavingsCreateView.as_view(), name='savings_create'),
     url(r'savings/(?P<pk>[\w]+)/$', SavingsUpdateView.as_view(), name='savings_edit'),
     url(r'savings/delete/(?P<pk>[\w]+)/$', SavingsDeleteView.as_view(), name='savings_delete'),

     url(r'season/list/$', SeasonFormListView.as_view(), name='season_list'),
     url(r'season/create/$', SeasonCreateView.as_view(), name='season_create'),
     url(r'season/(?P<pk>[\w]+)/$', SeasonUpdateView.as_view(), name='season_edit'),
     url(r'season/delete/(?P<pk>[\w]+)/$', SeasonDeleteView.as_view(), name='season_delete'),

     url(r'oko/location/list/$', OKOLocationListView.as_view(), name='oko_location_list'),
     url(r'oko/location/upload/$', OKOLocationUploadView.as_view(), name='oko_location_upload'),

     url(r'agent/list/$', AgentListView.as_view(), name='agent_list'),
     url(r'agent/create/$', AgentCreateFormView.as_view(), name='agent_create'),
     url(r'agent/edit/(?P<pk>[\w]+)/$', AgentCreateFormView.as_view(), name='agent_edit'),
     url(r'agent/detail/(?P<pk>[\w]+)/$', AgentDetailView.as_view(), name='agent_detail'),
     url(r'agent/password/(?P<pk>[\w]+)/$', AdminChangePasswordView.as_view(), name='agent_password'),
     url(r'agent/upload/$', AgentUploadView.as_view(), name='agent_upload'),
     url(r'agent/assign/device/(?P<pk>[\w]+)/$', AssignDeviceFormView.as_view(), name='assign_device'),
     url(r'agent/assign/card/(?P<pk>[\w]+)/$', AssignCardsFormView.as_view(), name='assign_card'),
     url(r'agent/agent/distribution/$', AgentMapView.as_view(), name='agent_map_view'),
     url(r'agent/agent/location/$', get_agent_location, name='agent_location'),

     url(r'collection/download/$', CollectionDownload.as_view(), name='collection_download'),
     url(r'collection/create/$', CollectionCreateView.as_view(), name='collection_update'),
     url(r'collection/create/$', CollectionCreateView.as_view(), name='collection_create'),
     url(r'collection/list/$', CollectionListView.as_view(), name='collection_list'),
     url(r'collection/upload/$', CollectionUploadView.as_view(), name='collection_upload'),

     url(r'member/shares/$', MemberSharesView.as_view(), name='member_shares'),

     url(r'member/insurance/create/(?P<pk>[\w]+)/$', OKOCreatePolicyView.as_view(), name='member_insurance_create'),
     url(r'member/insurance/check/(?P<pk>[\w]+)/$', OKOCheckPolicyView.as_view(), name='member_insurance_check'),
     
     url(r'member/shares/list/(?P<member>[\w]+)/$', MemberSharesListView.as_view(), name='member_shares_list'),
     url(r'member/shares/list/$', MemberSharesListView.as_view(), name='member_shares_list'),
     url(r'member/shares/create/$', MemberSharesCreateView.as_view(), name='member_shares_create'),
     url(r'member/shares/(?P<pk>[\w]+)/$', MemberSharesUpdateView.as_view(), name='member_shares_update'),

     url(r'member/registration/list/$', MemberRegistrationTransactionListView.as_view(), name='registration_list'),
     url(r'member/registration/create/$', MemberRegistrationTransactionCreateView.as_view(), name='registration_create'),
     
     url(r'member/subscription/list/$', MemberSubscriptionListView.as_view(), name='member_subscription_list'),
     url(r'member/subscription/create/$', MemberSubscriptionCreateView.as_view(), name='member_subscription_create'),
     url(r'member/subscription/(?P<pk>[\w]+)/$', MemberSubscriptionUpdateView.as_view(), name='member_subscription_update'),
     
     url(r'share/price/list/$', CooperativeSharePriceListView.as_view(), name='share_price_list'),
     url(r'share/price/create/$', CooperativeSharePriceCreateView.as_view(), name='share_price_create'),
     url(r'share/price/(?P<pk>[\w]+)/$', CooperativeSharePriceUpdateView.as_view(), name='share_price_update'),

     url(r'fee/price/list/$', CooperativeRegistrationFeeListView.as_view(), name='fee_list'),
     url(r'fee/price/create/$', CooperativeRegistrationFeeCreateView.as_view(), name='fee_create'),
     url(r'fee/price/(?P<pk>[\w]+)/$', CooperativeRegistrationFeeUpdateView.as_view(), name='fee_update'),
     
     url(r'supply/request/list/$', MemberSupplyRequestListView.as_view(), name='request_list'),
     url(r'supply/request/create/$', MemberSupplyRequestCreateView.as_view(), name='request_create'),
     url(r'supply/request/create/(?P<pk>[\w]+)/$', MemberSupplyRequestCreateView.as_view(), name='request_create'),
     url(r'supply/request/detail/(?P<pk>[\w]+)/$', MemberSupplyRequestDetailView.as_view(), name='request_detail'),
     
     
     url(r'ajax/village/$', load_villages, name='ajax_load_village'),
     url(r'ajax/member/$', load_coop_members, name='ajax_load_members'),
     
     url(r'communication/send/$', SendCommunicationView.as_view(), name='communication_send'),
     
     url(r'desease/list/$', CooperateCommonDiseaseListView.as_view(), name='disease_list'),
     url(r'desease/create/$', CooperateCommonDiseaseCreateView.as_view(), name='disease_create'),
     url(r'desease/(?P<pk>[\w]+)/$', CooperateCommonDiseaseUpdateView.as_view(), name='disease_update'),
     
     url(r'contribution/list/$', CooperativeContributionListView.as_view(), name='contribution_list'),
     url(r'contribution/create/$', CooperativeContributionCreateView.as_view(), name='contribution_create'),
     url(r'contribution/(?P<pk>[\w]+)/$', CooperativeContributionUpdateView.as_view(), name='contribution_update'),
     url(r'share/list/$', CooperativeShareTransactionListView.as_view(), name='share_list'),
     url(r'share/create/$', CooperativeShareTransactionCreateView.as_view(), name='share_create'),
     url(r'share/(?P<pk>[\w]+)/$', CooperativeShareTransactionUpdateView.as_view(), name='share_update'),
     url(r'member/delete/(?P<pk>[\w]+)/$', MemberDeleteView.as_view(), name='member_delete'),
     url(r'member/detail/(?P<pk>[\w]+)/$', CooperativeMemberDetailView.as_view(), name='member_detail'),
     url(r'member/qrcode/(?P<pk>[\w]+)/$', ImageQRCodeDownloadView.as_view(), name='member_qrcode'),
     url(r'member/download/$', DownloadExcelMemberView.as_view(), name='member_download'),
     url(r'member/upload/$', MemberUploadExcel.as_view(), name='member_upload'),
     url(r'member/list/$', CooperativeMemberListView.as_view(), name='member_list'),
     url(r'member/create/$', MemberCreateView.as_view(), name='member_create'),
     url(r'member/map/$', MembersMapView.as_view(), name='member_map'),
     url(r'member/(?P<pk>[\w]+)/$', MemberUpdateView.as_view(), name='member_update'),
     url(r'fg/create/$', FarmerGroupCreateView.as_view(), name='fg_create'),
     url(r'fg/list/$', FarmerGroupListView.as_view(), name='fg_list'),

     url(r'clan/delete/(?P<pk>[\w]+)/$', ClanDeleteView.as_view(), name='clan-delete'),
     url(r'clan/edit/(?P<pk>[\w]+)/$', ClanUpdateView.as_view(), name='clan-edit'),
     url(r'clan/upload/$', ClanUploadView.as_view(), name='clan-upload'),
     url(r'clan/create/$', ClanCreateView.as_view(), name='clan-create'),
     url(r'clan/list/$', ClanListView.as_view(), name='clan-list'),

     url(r'fg/edit/(?P<pk>[\w]+)/$', FarmerGroupUpdateView.as_view(), name='fg_edit'),
     url(r'fg/delete/(?P<pk>[\w]+)/$', FarmerGroupDeleteView.as_view(), name='fg_delete'),
     url(r'delete/(?P<pk>[\w]+)/$', CooperativeDeleteView.as_view(), name='delete'),
     url(r'upload/$', CooperativeUploadView.as_view(), name='upload'),
     url(r'create/$', CooperativeCreateView.as_view(), name='create'),
     url(r'list/$', CooperativeListView.as_view(), name='list'),
     url(r'ajax/load-farmer/', get_farmer_map, name='ajax_load_farmer_map'),
     url(r'ajax/load-fee/', ajax_load_fee, name='ajax_load_fee'),
     url(r'(?P<pk>[\w]+)/$', CooperativeUpdateView.as_view(), name='edit'),
     
    ]