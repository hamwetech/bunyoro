from django.conf.urls import url
from endpoint.views import *

urlpatterns = [
    url(r'order/oitem/list/(?P<order>[-\w]+)/$', OrderItemListView.as_view(), name='orderitem_list'),
    url(r'order/create/$', OrderCreateView.as_view(), name='order_create'),
    url(r'order/list/$', MemberOrderListView.as_view(), name='order_list'),
    url(r'cooperative/list', CooperativeListView.as_view(), name='cooperative_list'),
    url(r'sales/product/list/$', SalesProductView.as_view(), name='product_list'),
    url(r'unit/list/$', UnitView.as_view(), name='unit_list'),
    url(r'item/list/$', ItemView.as_view(), name='item_list'),
    url(r'supplier/list/$', SupplierView.as_view(), name='supplier_list'),
    url(r'category/list/$', CategoryView.as_view(), name='category_list'),
    url(r'collection/list/$', CollectionListView.as_view(), name='collection_list'),
    url(r'collection/create/$', CollectionCreateView.as_view(), name='collection_create'),
    url(r'training/update/(?P<session>[-\w\s]+)/$', TrainingSessionEditView.as_view(), name='training_update'),
    url(r'training/create/$', TrainingSessionView.as_view(), name='training_create'),
    url(r'training/list/$', TrainingSessionListView.as_view(), name='training_list'),
    url(r'member/list/(?P<member>[-\w\s]+)/$', MemberList.as_view(), name='member_list'),
    url(r'member/list/$', MemberList.as_view(), name='member_list'),

    url(r'oko/location/$', OKOLocationList.as_view(), name='oko_list'),
    url(r'oko/session/$', OKOSeasonList.as_view(), name='session_list'),
    url(r'oko/policy/$', OKOPolicyPurchaseView.as_view(), name='policy_purchase'),

    url(r'user/list/$', UserList.as_view(), name='user_list'),
    url(r'member/register/$', MemberEndpoint.as_view(), name='member_create'),
    url(r'member/register/ussd/$', USSDMemberEndpoint.as_view(), name='ussdmember_create'),
    url(r'agent/verify/$', AgentValidateView.as_view(), name='agent_verify'),
    url(r'device/coodinates/$', DeviceLocationListView.as_view(), name='location'),
    url(r'agent/detail/$', AgentProfileView.as_view(), name="agent_profile"),
    url(r'agent/gps/$', AgentGPSView.as_view(), name="agent_gps"),
    url(r'login/$', Login.as_view(), name='login'),
 ]
