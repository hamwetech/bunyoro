# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import datetime
import string
import random
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token

from django.forms.models import model_to_dict
from django.contrib.auth import authenticate

from userprofile.models import Profile, DeviceLocation
from product.models import ProductVariation, ProductVariationPrice, ProductUnit
from conf.models import District, County, SubCounty, Village
from coop.models import Cooperative, CooperativeMember, Collection, FarmerGroup
from activity.models import ThematicArea, TrainingModule, TrainingAttendance
from endpoint.serializers import *

from coop.views.member import save_transaction
from conf.utils import generate_numeric, generate_alpanumeric, genetate_uuid4, log_error, log_debug, get_message_template as message_template
from coop.utils import sendMemberSMS
from api.OKOTransactions import OKOTransaction


class Login(APIView):

    def post(self, request, format=None):
        serializer = LoginSerializer(data=request.data)
        try:
            if serializer.is_valid():
                data = request.data
                cooperative = False
                username = data.get('username')
                password = data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                #if hasattr(user.profile.access_level, 'name'):
                #if user.profile.access_level.name.lower()  == "cooperative" and user.cooperative_admin:
                #    cooperative = True
                #if cooperative:
                    q_token = Token.objects.filter(user=user)
                    if q_token.exists():
                        
                        token = q_token[0]
                        qs = Profile.objects.get(user=user)
                        product = Product.objects.values('name').all()
                        cooperatives = [{"id": c.id, "name": c.name, "code": c.code} for c in Cooperative.objects.all().order_by('name')]
                        members = CooperativeMember.objects.all().order_by('-surname')
                        variation = ProductVariation.objects.values('id', 'product', 'name').all()
                        variation_price = ProductVariationPrice.objects.values('id', 'product', 'product__name', 'price').all()
                        district = District.objects.values('id', 'name').all()
                        county = County.objects.values('id', 'district', 'name').all()
                        farmer_group = FarmerGroup.objects.values('id', 'cooperative', 'name').all()
                        sub_county = SubCounty.objects.values('id', 'county', 'name').all()
                        village = Village.objects.values('id', 'parish', 'parish__sub_county', 'name').all()
                        thematic_area = ThematicArea.objects.values('id', 'thematic_area').all()
                        user_type = user.profile.access_level.name.upper() if user.profile.access_level else "NONE"
                        items = Item.objects.all()
                        items_data = ItemSerializer(items,  many=True)
                        categories  = Category.objects.all()
                        category_data = CategorySerializer(categories, many=True)
                        suppliers = Supplier.objects.all()
                        supplier_data = SupplierSerializer(suppliers, many=True)
                        units = ProductUnit.objects.all()
                        unit_data = UnitSerializer(units, many=True)
                        user_farmer_groups = [i.farmer_group.id for i in FarmerGroupAdmin.objects.filter(user=user)]
                        user_cooperatives = [i.cooperative.id for i in CooperativeAdmin.objects.filter(user=user)]


                        is_admin = user.is_superuser
                        cooperative = None
                        if hasattr(user.profile.access_level, 'name'):
                            if user.profile.access_level == "COOPERATIVE":
                                if user.cooperative_admin:
                                    members = members.filter(cooperative=cooperative)
                                    cooperative = {"name": user.cooperative_admin.cooperative.name,
                                                   "id": user.cooperative_admin.cooperative.id,
						   "code": user.cooperative_admin.cooperative.code}
                        return Response({
                            "status": "OK",
                            "token": token.key,
                            "user": {"username": qs.user.username, "id": qs.user.id, "user_type": user_type, "is_admin": is_admin,
                                     "user_farmer_groups":user_farmer_groups, "user_cooperatives":user_cooperatives},
                            "cooperative": cooperative,
                            "cooperatives": cooperatives,
                            "items": items_data.data,
                            "categories": category_data.data,
                            "suppliers": supplier_data.data,
                            "units": unit_data.data,
                            "product": product,
                            "variation": variation,
                            "variation_price": variation_price,
                            "district": district,
                            "county": county,
                            "farmer_group": farmer_group,
                            "members": [],#MemberListSerializer(members, many=True).data,
                            "sub_county": sub_county,
                            "village": village,
                            "thematic_area": thematic_area,
                            "response": "Login success"
                            }, status.HTTP_200_OK)
                    return Response({"status": "ERROR", "response": "Access Denied"}, status.HTTP_200_OK)
                        
                return Response({"status": "ERROR", "response": "Invalid Username or Password"}, status.HTTP_200_OK)
        except Exception as err:
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentValidateView(APIView):

    def post(self, request, format=None):
        phone_number = request.data.get('phone_number')
        agent_code = request.data.get('agent_code')
        profiles = Profile.objects.filter(msisdn=phone_number)

        if profiles.exists():
            profile = profiles[0]
            q_token = Token.objects.filter(user=profile.user)
            if q_token.exists():
                cooperatives = [{"id": c.cooperative.id, "name": c.cooperative.name, "code": c.cooperative.code} for c
                                in
                                OtherCooperativeAdmin.objects.filter(user=profile.user)]

                token = q_token[0]
                return Response({"status": "OK", "response": {"token": token.key, "cooperatives": cooperatives }}, status.HTTP_200_OK)
        return Response({"status": "ERROR", "response": "Agent not Found"}, status.HTTP_200_OK)


class MemberEndpoint(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = [FormParser, MultiPartParser, FileUploadParser]
    
    def post(self, request, format=None):
        farmer_group = request.data.get('farmer_group')
        cooperative = request.data.get('cooperative')
        log_debug("FArmer Group 1 %s" % farmer_group)
        if farmer_group or farmer_group != "":
            fgs = FarmerGroup.objects.filter(pk=farmer_group)
            log_debug("FArmer Group 2 %s" % fgs)

            if not fgs.exists():
                request.data['farmer_group'] = None
        else:
            request.data['farmer_group'] = None

        if cooperative or cooperative !="":
            coops = Cooperative.objects.filter(pk=cooperative)
            if not coops.exists():
                request.data['cooperative'] = None
        else:
            request.data['cooperative'] = None

        log_debug("XXXX Farmer Submission Request from User %s XXXX" % (self.request.user))
        print("XXXX Farmer Submission Request from User %s XXXX" % (self.request.user))

        if request.data.get('farmer_group') == "0":
            request.data['farmer_group'] = None
        print(request.data)
        log_debug(request.data)
        log_debug("FArmer Group 2 %s" % fgs)
        member = MemberSerializer(data=request.data)
        mem = CooperativeMember.objects.filter(member_id=request.data.get('member_id'))
        if mem.count() < 1:
            print("%s %s %s %s %s" % (request.data.get('first_name'), request.data.get('other_name'), request.data.get('surname'), request.data.get('date_of_birth'),request.data.get('id_number')))
            mem = CooperativeMember.objects.filter(first_name=request.data.get('first_name'),surname=request.data.get('surname'),date_of_birth=request.data.get('date_of_birth'), id_number=request.data.get('id_number'))
            print("Members Found %s" % mem.count())
        print ("ADDING........%s, %s " % (mem.count(), request.data.get('member_id')))
        log_debug ("ADDING........%s, %s " % (mem.count(), request.data.get('member_id')))
        log_debug ("Farmer Group........%s, %s " % (request.data['farmer_group'] , request.data.get('member_id')))
        if mem.count() > 0:
            member = MemberSerializer(mem[0], data=request.data) 
        try:
            if member.is_valid():
                
                with transaction.atomic():

                    if mem.count() < 1: 
                        __member = member.save()
                        __member.member_id = self.generate_member_id(__member)
                        __member.create_by = request.user
                        __member.save()
                        mes = message_template()
                        print('Saved  Record %s' % __member.member_id)
                        log_debug('Saved  Record %s' % __member.member_id)
                        if mes:
                            message = message_template().member_registration
                            if re.search('<NAME>', message):
                                if __member.surname:
                                    message = message.replace('<NAME>', '%s %s' % (__member.surname.title(), __member.first_name.title()))
                                    # if cooperative:
                                    #     message = message.replace('<COOPERATIVE>', __member.cooperative.name)
                                    # if fgs:
                                    #     message = message.replace('<COOPERATIVE>', __member.farmer_group.name)
                                    message = message.replace('<IDNUMBER>', __member.member_id)
                                    sendMemberSMS(request, __member, message)
                    else:
                        print("UPDATING....%s" % request.data)
                        log_debug("UPDATING....%s" % request.data)
                        log_debug("FG....%s" % request.data.get("farmer_group"))
                        log_debug("consumer_device_id....%s" % request.data.get("consumer_device_id"))
                        log_debug("consent_id....%s" % request.data.get("consent_id"))
                        log_debug("cpk_rid....%s" % request.data.get("cpk_rid"))
                        log_debug("create_wallet....%s" % request.data.get("create_wallet"))
                        __member = mem[0]
                        # updated = CooperativeMember.objects.filter(member_id=request.data.get('member_id')).update(
                        #     image=request.data.get("image"),
                        #     surname=request.data.get("surname"),
                        #     first_name=request.data.get("first_name"),
                        #     other_name=request.data.get("other_name"),
                        #     date_of_birth=request.data.get("date_of_birth"),
                        #     gender=request.data.get("gender"),
                        #     farmer_group=request.data.get("farmer_group"),
                        #     maritual_status=request.data.get("maritual_status"),
                        #     phone_number=request.data.get("phone_number"),
                        #     id_number=request.data.get("nin"),
                        #     # own_phone=request.data.get("own_phone"),
                        #     # has_mobile_money=request.data.get("has_mobile_money"),
                        #     email=request.data.get("email"),
                        #     district=request.data.get("district"),
                        #     county=request.data.get("county"),
                        #     sub_county=request.data.get("sub_county"),
                        #     village=request.data.get("village"),
                        #     coop_role=request.data.get("coop_role"),
                        #     land_acreage=request.data.get("land_acreage"),
                        #     product=request.data.get("product"),
                        #     cpk_rid = request.data.get("cpk_rid"),
                        #     passcode = request.data.get("passcode"),
                        #     consent_id = request.data.get("consent_id"),
                        #     consumer_device_id = request.data.get("consumer_device_id"),
                        # )
                        # log_debug("Updated Data %s" % updated)
                        fgs = FarmerGroup.objects.filter(pk=request.data.get("farmer_group"))
                        d = District.objects.filter(pk=request.data.get("district"))
                        c = County.objects.filter(pk=request.data.get("county"))
                        sc = SubCounty.objects.filter(pk=request.data.get("sub_county"))
                        v  = Village.objects.filter(pk=request.data.get("village"))

                        __member.image = request.data.get("image")
                        __member.surname = request.data.get("surname")
                        __member.first_name = request.data.get("first_name")
                        __member.other_name = request.data.get("other_name")
                        __member.date_of_birth = request.data.get("date_of_birth")
                        __member.gender = request.data.get("gender")
                        __member.farmer_group = fgs[0] if fgs.exists() else None
                        __member.maritual_status = request.data.get("maritual_status")
                        __member.phone_number = request.data.get("phone_number")
                        __member.id_number = request.data.get("id_number")
                        __member.email = request.data.get("email")
                        __member.create_wallet = bool(request.data.get("own_phone"))
                        __member.create_wallet = bool(request.data.get("has_mobile_money"))
                        __member.create_wallet = bool(request.data.get("create_wallet"))
                        __member.district = d[0] if d.exists() else None
                        __member.county = c[0] if c.exists() else None
                        __member.sub_county = sc[0] if sc.exists() else None
                        __member.village = v[0].name if v.exists() else None
                        __member.coop_role = request.data.get("coop_role")
                        __member.land_acreage = request.data.get("land_acreage")
                        __member.product = request.data.get("product")
                        __member.cpk_rid = request.data.get("cpk_rid")
                        __member.passcode = request.data.get("passcode")
                        __member.consent_id = request.data.get("consent_id")
                        __member.consumer_device_id = request.data.get("consumer_device_id")
                        __member.image=request.data.get("image")
                        __member.save()
                    return Response(
                        {"status": "OK", "response": "Farmer Profile Saved Successfully", "member_id": __member.member_id, "id": __member.id},
                        status.HTTP_200_OK)
            print(member.errors)
            log_debug(member.errors)
            return Response(member.errors)
        except Exception as err:
            print(err)
            log_debug(err)
            log_error()
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(member.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def safe_get(self, _model, _value):
        try:
            return get_object_or_404(_model, cooperative_member=_value)
        except Exception:
            return None
    
    def generate_member_id(self, member):
        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        fint = "%04d"%member.id
        idno = generate_numeric(size=4)+yr+fint
        log_debug("FsrmerID is %s" % (idno))
        print("FarmerID is %s" % (idno))
        return idno
    
    def check_id(self, member, cooperative, count, yr):
        fint = "%04d"%count
        idno = str(cooperative.code)+yr+fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            print ("iteration count %s" % count)
            return self.check_id(member, cooperative, count, yr)
        return idno


class USSDMemberEndpoint(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        member = MemberSerializer(data=request.data)
        farmer_name = "%s %s %s" % (request.data.get('first_name'), request.data.get('surname'), request.data.get('other_name'))
        mem = CooperativeMember.objects.annotate(farmer_name=Concat('first_name', Value(' '), 'surname', Value(' '), 'other_name')).filter(Q(farmer_name=farmer_name)| Q(phone_number=request.data.get("phone_number")))
        log_debug("ADDING........%s, %s " % (mem.count(), request.data))
        if mem.count() > 0:
            member = MemberSerializer(mem[0], data=request.data)
        try:
            if member.is_valid():

                with transaction.atomic():
                    if mem.count() < 1:
                        __member = member.save()
                        __member.member_id = self.generate_member_id(__member.cooperative)
                        __member.create_by = request.user
                        __member.save()
                        mes = message_template()
                        if mes:
                            message = message_template().member_registration
                            if re.search('<NAME>', message):
                                if __member.surname:
                                    message = message.replace('<NAME>', '%s %s' % (
                                    __member.surname.title(), __member.first_name.title()))
                                    message = message.replace('<COOPERATIVE>', __member.cooperative.name)
                                    message = message.replace('<IDNUMBER>', __member.member_id)
                                    sendMemberSMS(request, __member, message)
                    else:
                        log_debug("UPDATING....%s" % request.data)
                        __member = mem[0]
                        CooperativeMember.objects.filter(member_id=request.data.get('member_id')).update(
                            image=request.data.get("image"),
                            surname=request.data.get("surname"),
                            first_name=request.data.get("first_name"),
                            other_name=request.data.get("other_name"),
                            date_of_birth=request.data.get("date_of_birth"),
                            gender=request.data.get("gender"),
                            id_number=request.data.get("nin"),
                            maritual_status=request.data.get("maritual_status"),
                            phone_number=request.data.get("phone_number"),
                            email=request.data.get("email"),
                            district=request.data.get("district"),
                            county=request.data.get("county"),
                            sub_county=request.data.get("sub_county"),
                            village=request.data.get("village"),
                            coop_role=request.data.get("coop_role"),
                            land_acreage=request.data.get("land_acreage"),
                            product=request.data.get("product"),
                            is_refugee=request.data.get("is_refugee"),
                            seed_multiplier=request.data.get("seed_multiplier"),
                            cpk_rid=request.data.get("cpk_rid"),
                            passcode=request.data.get("passcode"),
                            consent_id=request.data.get("consent_id"),
                            consumer_device_id=request.data.get("consumer_device_id"),
                        )
                    return Response(
                        {"status": "OK", "response": "Farmer Profile Saved Successfully",
                         "member_id": __member.member_id},
                        status.HTTP_200_OK)
            return Response(member.errors)
        except Exception as err:
            return Response({"status": "ERROR", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(member.errors, status=status.HTTP_400_BAD_REQUEST)

    def safe_get(self, _model, _value):
        try:
            return get_object_or_404(_model, cooperative_member=_value)
        except Exception:
            return None

    def generate_member_id(self, cooperative):
        member = CooperativeMember.objects.all()
        count = member.count() + 1

        today = datetime.today()
        datem = today.year
        yr = str(datem)[2:]
        # idno = generate_numeric(size=4, prefix=str(m.cooperative.code)+yr)
        # fint = "%04d"%count
        # idno = str(cooperative.code)+yr+fint
        # member = member.filter(member_id=idno)
        idno = self.check_id(member, cooperative, count, yr)
        log_debug("Cooperative %s code is %s" % (cooperative.code, idno))
        return idno

    def check_id(self, member, cooperative, count, yr):
        fint = "%04d" % count
        idno = str(cooperative.code) + yr + fint
        member = member.filter(member_id=idno)
        if member.exists():
            count = count + 1
            print
            "iteration count %s" % count
            return self.check_id(member, cooperative, count, yr)
        return idno


class CooperativeListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, member=None, format=None):
        cooperatives = Cooperative.objects.all()
        serializer = CooperativeSerializer(cooperatives, many=True)
        return Response(serializer.data)


class AgentProfileView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, member=None, format=None):
        user = Profile.objects.get(pk=request.user.pk)
        serializer = AgentSerializer(user, context={'request': request}, many=False)
        return Response(serializer.data)


class AgentGPSView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, member=None, format=None):
        user = self.request.user
        gps_coordinates = request.data.get('gps_coordinates')
        profile = Profile.objects.get(user=user)
        profile.gps_coodinates = gps_coordinates
        profile.save()
        return Response(
            {"status": "OK", "response": "Agent GPS Saved Saved"},
            status.HTTP_200_OK)
    
class MemberList(APIView):

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, member=None, format=None):
        cooperative = request.data.get('cooperative')  
        # members = CooperativeMember.objects.filter(cooperative=request.user.cooperative_admin.cooperative).order_by('-surname')
        if cooperative == 'all':
            members = CooperativeMember.objects.all().order_by('-surname')
        else:
            if cooperative:
                members = CooperativeMember.objects.filter(cooperative=cooperative).order_by('-surname')
            else:
                members = CooperativeMember.objects.filter(create_by=request.user).order_by('-surname')
        if member:
            members = members.filter(Q(member_id=member)|Q(phone_number=member)|Q(other_phone_number=member))
        serializer = MemberListSerializer(members, many=True)
        return Response(serializer.data)
    

class TrainingSessionView(APIView):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        pk = request.data.get('session_id')
        print (pk)
        training = TrainingSessionSerializer(data=request.data)
        
        try:
            if pk:
                ts = TrainingSession.objects.get(pk=pk)
                print(ts)
                training = TrainingSessionUpdateSerializer(ts, data=request.data)
            print request.data
            if training.is_valid():
                print training
                with transaction.atomic():
                    ta = request.data.get('thematic_area')
                    tq = ThematicArea.objects.filter(pk=ta)
                    __training = training.save(thematic_area=tq[0])
                    __training.trainer = request.user
                    __training.created_by = request.user
                    if not pk:
                        __training.training_reference = generate_alpanumeric(prefix="TR", size=8)
                    __training.save()
                    
                    #get Member list
                    data = request.data
                    if pk:
                        __training.coop_member.clear()
                    for m in data.get('member'):
                        member = CooperativeMember.objects.get(member_id=m)
                        __training.coop_member.add(member)
                    
                    return Response(
                        {"status": "OK", "response": "Training Session Saved"},
                        status.HTTP_200_OK)
            
            return Response(training.errors)
        except Exception as err:
            log_error()
            return Response({"status": "ERRORf", "response": err}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(training.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class TrainingSessionListView(APIView):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        farmer_group = request.data.get('farmer_group')
        cooperative = request.data.get('cooperative')
        fgs = FarmerGroup.objects.filter(pk=farmer_group)
        coops = Cooperative.objects.filter(pk=farmer_group)
        if not fgs.exists():
            request.data['farmer_group'] = None
        if not coops.exists():
            request.data['cooperative'] = None
        if request.data.get('farmer_group') == "0":
            request.data['farmer_group'] = None
        print(request.data)
        training = TrainingSession.objects.filter(cooperative=cooperative).order_by('-create_date')
        # training = TrainingSession.objects.all().order_by('-create_date')
        serializer = TrainingSessionSerializer(training, many=True)
        return Response(serializer.data)
    

class TrainingSessionEditView(APIView): #DRY thrown out here. Need fix
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, session, format=None):
        cooperative = request.data.get('cooperative')
        print "Cooperative" + cooperative
        training = TrainingSession.objects.filter(cooperative=cooperative, pk=session).order_by('-create_date')
        # training = TrainingSession.objects.all().order_by('-create_date')
        serializer = TrainingSessionEditSerializer(training, many=True)
        return Response(serializer.data)
    
    
class CollectionCreateView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        collection = CollectionSerializer(data=request.data)
        if collection.is_valid():
            try:
                with transaction.atomic():
                    c = collection.save(created_by = request.user)
                    # collection_date = data.get('collection_date')
                    # is_member = data.get('is_member')
                    # member = data.get('member')
                    # name = data.get('name')
                    # phone_number = data.get('phone_number')
                    # collection_reference = data.get('collection_reference')
                    # product = data.get('product')
                    # quantity = data.get('quantity')
                    # unit_price = data.get('unit_price')
                    # total_price = data.get('total_price')
                    # created_by = data.get('created_by')
                    if c.is_member:
                        params = {
                            'amount': c.total_price,
                            'member': c.member,
                            'transaction_reference': c.collection_reference ,
                            'transaction_type': 'COLLECTION',
                            'entry_type': 'CREDIT'
                        }
                        member = CooperativeMember.objects.filter(pk=c.member.id)
                        if member.exists():
                            member = member[0]
                            qty_bal = member.collection_quantity if member.collection_quantity else 0
                            new_bal = c.quantity + qty_bal
                            member.collection_quantity = new_bal
                            member.save()
                        save_transaction(params)
                        new_member = CooperativeMember.objects.get(pk=c.member.id)
                        collection_count = Collection.objects.filter(member=member)
                        colections_list= []
                        if collection_count.exists():
                            colections_list = [{"id": cl.id, "product_id": cl.product.id,
                                                "product_name": cl.product.name, "product_weight": cl.quantity,
                                                "unit_price": cl.unit_price, "total_price": cl.total_price, "timestamp":cl.collection_date} for cl in collection_count]
                        try:
                            message = message_template().collection
                            message = message.replace('<NAME>', member.surname)
                            message = message.replace('<QTY>', "%s%s" % (c.quantity, c.product.unit.code))
                            message = message.replace('<PRODUCT>', "%s" % (c.product.name))
                            message = message.replace('<COOP>', c.cooperative.name)
                            message = message.replace('<DATE>', c.collection_date.strftime('%Y-%m-%d'))
                            message = message.replace('<AMOUNT>', "%s" % c.total_price)
                            message = message.replace('<REFNO>', c.collection_reference)
                            sendMemberSMS(self.request, member, message)
                        except Exception:
                            log_error()

                    return Response(
                                {"status": "OK", "response": "Collection Saved.", "data": {"member_name": member.get_name(),
                                                                                           "total_collection_amount": new_member.collection_amount,
                                                                                           "total_collection_count": collection_count.count(),
                                                                                           "total_collection_quantity": new_member.collection_quantity,
                                                                                           "account_balance": new_member.account_balance,
                                                                                           "collections_list": colections_list
                                                                                           }
                                 },
                                status.HTTP_200_OK)
            except Exception as e:
                log_error()
                return Response({"status": "ERROR", "response": "error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(collection.errors)
            

class CollectionListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        #raise Exception(request.user)
        cooperative = request.data.get('cooperative')
        if cooperative:
            collections = Collection.objects.filter(cooperative=cooperative).order_by('-create_date')
        else:
            collections = Collection.objects.all().order_by('-create_date')
        serializer = CollectionListSerializer(collections, many=True)
        return Response(serializer.data)
    

class MemberOrderListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        cooperative = request.data.get('cooperative')
        if cooperative:
            orders = MemberOrder.objects.filter(cooperative=cooperative).order_by('-create_date')
        else:
            orders = MemberOrder.objects.all().order_by('-create_date')
        serializer = MemberOrderSerializer(orders, many=True)
        return Response(serializer.data)


class SalesProductView(APIView):
    # authentication_classes = (TokenAuthentication,)
    # permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        units = ProductUnit.objects.all()
        items = Item.objects.all()
        supplier = Supplier.objects.all()
        category = Category.objects.all()
        category_serializer = CategorySerializer(category, many=True)
        supplier_serializer = SupplierSerializer(supplier, many=True)
        items_serializer = ItemSerializer(items, many=True)
        units_serializer = UnitSerializer(units, many=True)
        return Response( {"status": "OK", "response": {"categories": category_serializer.data,
                                                       "suppliers": supplier_serializer.data,
                                                       "units": units_serializer.data,
                                                       "items": items_serializer.data,
                                                       }
                          },
                                status.HTTP_200_OK)


class OrderItemListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, order, format=None):
        order_items = OrderItem.objects.filter(order=order).order_by('-create_date')
        serializer = OrderItemSerializer(order_items, many=True)
        return Response(serializer.data)




class UnitView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        units = ProductUnit.objects.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)


class ItemView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        items = Item.objects.all()
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data)


class SupplierView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        supplier = Supplier.objects.all()
        serializer = SupplierSerializer(supplier, many=True)
        return Response(serializer.data)


class CategoryView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        items = Category.objects.all()
        serializer = CategorySerializer(items, many=True)
        return Response(serializer.data)
    
    
class OrderCreateView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, format=None):
        data = request.data 
        mo = MemberOrderFormSerializer(data=data)
        if mo.is_valid():
            _order = mo.save(created_by=request.user)
            for i in data.get("item"):
                oi = OrderItemSerializer_(data=i)
                if oi.is_valid():
                    oi.save(order=_order, created_by=request.user)
                else:
                    return Response(oi.errors)
            return Response({"status": "OK", "response": "Order Saved"}, status.HTTP_200_OK)
        return Response(mo.errors)


class UserList(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        data = request.data
        users = Profile.objects.all()
        serializer = AgentSerializer(users, context={'request': request}, many=True)
        return Response(serializer.data)


class DeviceLocationListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        device_location = DeviceLocationSerializer(data=request.data)
        try:
            with transaction.atomic():
                if device_location.is_valid():
                    c = device_location.save(assigned_to = request.user)
                    return Response(
                                {"status": "OK", "response": "Location Saved."},
                                status.HTTP_200_OK)
        except Exception as e:
            log_error()
            return Response({"status": "ERROR", "response": "error"}, status.HTTP_200_OK)
        return Response(device_location.data)


class OKOLocationList(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        data = request.data
        ol = OKOLocation.objects.all()
        serializer = OKOLocationSerializer(ol,  many=True)
        return Response(serializer.data)


class OKOSeasonList(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        data = request.data
        ol = Season.objects.all()
        serializer = OKOSeasonSerializer(ol,  many=True)
        return Response(serializer.data)


class OKOPolicyPurchaseView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        policy = OKOMemberPolicySerializer(data=request.data)
        if policy.is_valid():
            try:
                with transaction.atomic():
                    member_id = request.data.get('member_id')
                    sub_county = request.data.get('sub_county')
                    season_id = request.data.get('season_id')
                    member = CooperativeMember.objects.get(member_id=member_id)
                    district = OKOLocation.objects.get(pk=sub_county)

                    payload = {
                        "district": {
                            "name": district.district
                        },
                        "county": "",
                        "sub_county": district.sub_county,
                        "member_id": member.member_id,
                        "surname": member.surname,
                        "first_name": member.first_name,
                        "other_name": member.other_name if member.other_name else "",
                        "gender": member.gender,
                        "date_of_birth": member.date_of_birth.strftime('%Y-%m-%d') if member.date_of_birth else "",
                        "phone_number": member.phone_number.replace("256", "") if member.phone_number else "",
                        "land_acreage": str(member.land_acreage) if member.land_acreage else "",
                        "seasonId": season_id
                    }

                    print(payload)
                    try:
                        if member.land_acreage:
                            oko = OKOTransaction()
                            res = oko.CreatePolicyPartner(payload)

                            if "policyId" in res and res.get('policyId'):
                                policyId = res.get('policyId')
                                amountDue = res.get('amountDue')

                                try:
                                    season = Season.objects.get(session_id=season_id)
                                except Exception as e:
                                    season = None

                                qs = OKOMemberPolicy.objects.filter(policyId=policyId)
                                if qs.exists():
                                    qs = qs[0]
                                    qs.amount_due = amountDue
                                    if season:
                                        qs.season = season
                                    qs.save()
                                else:
                                    OKOMemberPolicy.objects.create(
                                        cooperative_member=member,
                                        season=season,
                                        policyId=policyId,
                                        amount_due=amountDue,
                                        created_by=request.user
                                    )
                                return Response(
                                    {"status": "OK", "response": "Policy Created Saved.", "data": {"policyId": policyId, "amountDue": amountDue}},
                                    status.HTTP_200_OK)
                            else:
                                return Response({"status": "ERROR", "response": "Policy Creation Failed. Cannot reach OKO. Contact Admin", "data": {}},
                                status.HTTP_200_OK)
                        else:
                            return Response({"status": "ERROR", "response": "Please provide the Agents Land Acreage", "data": {}},
                                            status.HTTP_200_OK)
                    except Exception as e:
                        log_error()
                        return Response(
                            {"status": "ERROR", "response": "Policy creation failed. Contact Admin", "data": {} }, status.HTTP_200_OK)
            except Exception as e:
                log_error()
                return Response({"status": "ERROR", "response": "error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(policy.errors)