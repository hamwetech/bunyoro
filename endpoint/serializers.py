from datetime import datetime, date
from rest_framework import serializers
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from coop.models import *
from conf.models import *
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from userprofile.models import Profile, AccessLevel, DeviceLocation
from product.models import *
from conf.utils import internationalize_number, log_debug, log_error
from activity.models import ThematicArea, TrainingSession, TrainingModule


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=128)
    password = serializers.CharField(max_length=128)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ['create_date']

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        exclude = ['create_date', 'update_date']


class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = ['id', 'name']


class SubCountySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCounty
        exclude = ['create_date', 'update_date']


class CooperativeMemberBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = CooperativeMemberBusiness
        exclude = ['create_date', 'update_date']
        

class CooperativeMemberSupplySerializer(serializers.ModelSerializer):
    class Meta:
        model = CooperativeMemberSupply
        exclude = ['create_date', 'update_date']
      

class CooperativeMemberProductDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CooperativeMemberProductDefinition
        exclude = ['create_date', 'update_date']
      

class CooperativeMemberProductQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CooperativeMemberProductQuantity
        exclude = ['create_date', 'update_date']


class CooperativeSerializer(serializers.ModelSerializer):
    union = serializers.SerializerMethodField('is_named_union')
    members = serializers.SerializerMethodField('member_count')

    def is_named_union(self, obj):
        return "%s" % settings.PRODUCT_ABBREVIATION
    
    def member_count(self, obj):
        m = CooperativeMember.objects.filter(cooperative=obj)
        return m.count()

    class Meta:
        model = Cooperative
        fields = ['id', 'name', 'union', 'members']


class MemberListSerializer(serializers.ModelSerializer):

    cooperative = CooperativeSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    county = CountySerializer(read_only=True)
    sub_county = SubCountySerializer(read_only=True)
    age = serializers.SerializerMethodField('calculate_age')

    def calculate_age(self, obj):
        if obj.date_of_birth:
            m = date.today() - obj.date_of_birth
            return m.days / 365
        return 0

    class Meta:
        model = CooperativeMember
        exclude = ['update_date']


        
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CooperativeMember
        exclude = ['update_date']
 
    def validate(self, data):
        phone_number = data.get('phone_number')
        other_phone_number = data.get('other_phone_number')
        first_name = data.get('first_name')
        surname = data.get('surname')
        other_name = data.get('other_name')
        other_phone_number = data.get('other_phone_number')
        id_number = data.get('id_number')
        date_of_birth = data.get('date_of_birth')
        farmer_group = data.get('farmer_group')

        # if not farmer_group:
        #     data['farmer_group'] = None
        # if farmer_group == "0":
        #     data['farmer_group'] = None
        # data['farmer_group'] = None
        # if id_number == "":
        #     data['id_number'] = None


        if date_of_birth:
            if date_of_birth > timezone.now().date():
                raise serializers.ValidationError("Error! Date of Birth cannot be in the Future")
        
        if phone_number:
            try:
                phone_number = internationalize_number(phone_number)
                data['phone_number'] = phone_number
            except ValueError:
                raise serializers.ValidationError("Please enter a valid phone number.'%s' is not valid" % phone_number)
            
            # member = CooperativeMember.objects.filter(phone_number=phone_number, first_name=first_name, surname=surname, other_name=other_name)
            # if member.exists():
            #     raise serializers.ValidationError("The phone number.'%s' is arleady in use. Please provide another number" % phone_number)
        
        if other_phone_number:
            try:
                other_phone_number = internationalize_number(other_phone_number)
                data['other_phone_number'] = other_phone_number
            except ValueError:
                raise serializers.ValidationError("Please enter a valid phone number.'%s' is not valid" % other_phone_number)
        return data

    def update(self, instance, validated_data):
        print("SERIALIZER UPDATE")
        instance.save()
        return instance


class ProductVariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariation
        fields = ['product', 'name', 'id']


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        exclude = ['create_date', 'update_date']


class CollectionListSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    product = ProductVariationSerializer(read_only=True)
    cooperative = CooperativeSerializer(read_only=True)
    class Meta:
        model = Collection
        fields = ['id', 'collection_date', 'is_member', 'name', 'phone_number', 'collection_reference', 'quantity', 'unit_price', 'total_price', 'cooperative', 'member', 'product', 'created_by']

        
class TrainingModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingModule
        fields = ['thematic_area', 'topic', 'descriprion']
   
        
class ThematicAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThematicArea
        fields = ['id', 'thematic_area']
        
        
class TrainingSessionSerializer(serializers.ModelSerializer):
    thematic_area = ThematicAreaSerializer(read_only=True)
    trainer = UserSerializer(read_only=True)
    #coop_member = MemberSerializer(many=True)
    class Meta:
        model = TrainingSession
        exclude = ['created_by', 'create_date', 'update_date']
        

class TrainingSessionEditSerializer(serializers.ModelSerializer):
    thematic_area = ThematicAreaSerializer(read_only=True)
    trainer = UserSerializer(read_only=True)
    coop_member = MemberSerializer(many=True, allow_null=True)
    class Meta:
        model = TrainingSession
        exclude = ['created_by', 'create_date', 'update_date']
        
        
class TrainingSessionUpdateSerializer(serializers.ModelSerializer):
    thematic_area = ThematicAreaSerializer(read_only=True)
    trainer = UserSerializer(read_only=True)
    coop_member = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = TrainingSession
        exclude = ['created_by', 'create_date', 'update_date']
        
    def create(self, validated_data):
        return TrainingSession.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.thematic_area = validated_data.get('thematic_area', instance.thematic_area)
        instance.topic = validated_data.get('topic', instance.topic)
        instance.descriprion = validated_data.get('descriprion', instance.descriprion)
        instance.training_start = validated_data.get('training_start', instance.training_start)
        instance.training_end = validated_data.get('training_end', instance.training_end)
        instance.save()
        return instance


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUnit
        exclude = ['create_date', 'update_date']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        exclude = ['create_date', 'update_date']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ['create_date', 'update_date']


class ItemSerializer(serializers.ModelSerializer):
    supplier  = SupplierSerializer(read_only=True)
    category  = SupplierSerializer(read_only=True)
    unit  = UnitSerializer(read_only=True)

    class Meta:
        model = Item
        fields = ['id', 'name', 'unit', 'category',  'supplier', 'price']
        

class MemberOrderSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    cooperative = CooperativeSerializer(read_only=True)
    class Meta:
        model = MemberOrder
        exclude = ['update_date']
        

class MemberOrderFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberOrder
        exclude = ['update_date']


class OrderItemSerializer(serializers.ModelSerializer):
    order = MemberOrderSerializer(read_only=True)
    item = ItemSerializer(ItemSerializer)
    class Meta:
        model = OrderItem
        fields = ['order', 'item', 'quantity', 'price', 'unit_price', 'create_date']
        

class OrderItemSerializer_(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ['update_date']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password']


class AccessLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLevel
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    access_level = AccessLevelSerializer(read_only=True)
    members = serializers.SerializerMethodField('member_count')
    union = serializers.SerializerMethodField('is_named_union')
    
    def is_named_union(self, obj):
        return "%s" % settings.PRODUCT_ABBREVIATION

    def member_count(self, obj):
        req = self.context.get('request')
        m = CooperativeMember.objects.filter(create_by=obj.user)
        start_date = req.data.get('start_date')
        end_date = req.data.get('end_date')
        if start_date:
            m = m.filter(create_date__gte=start_date)
        if end_date:
            m = m.filter(create_date__lte=end_date)
        return m.count()

    class Meta:
        model = Profile
        exclude = ['update_date']


class DeviceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceLocation
        exclude = ['update_date']


class OKOLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OKOLocation
        exclude = ['update_date', 'create_date']


class OKOSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        exclude = ['update_date', 'create_date']


class OKOMemberPolicySerializer(serializers.Serializer):
    member_id = serializers.CharField(max_length=128)
    season_id = serializers.CharField(max_length=128)
    sub_county = serializers.IntegerField()

