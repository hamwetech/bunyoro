# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.db.models import Sum
from django.views.generic import TemplateView
from django.db.models import Q, CharField, Max, Sum, Count, Value as V
from django.db.models.functions import Concat
from coop.models import *
from activity.models import *
from payment.models import *
from credit.models import *
from django.db.models import Sum
from django.db.models import Count
from datetime import date
from django.utils.dates import MONTHS
from django.db.models.functions import TruncDate
from userprofile.models import Profile, Device, AssignedCards
from product.models import ProductVariationPrice, Supplier
from messaging.models import OutgoingMessages
from django.http import JsonResponse

class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        cooperatives = Cooperative.objects.all()
        clans = Clan.objects.all()
        members = CooperativeMember.objects.all()
        suppliers = Supplier.objects.all()
        orders = MemberOrder.objects.all()
        loans = LoanRequest.objects.all()
        sum_loans = loans.filter(status='APPROVED').aggregate(sum=Sum('requested_amount'))
        agents = Profile.objects.filter(access_level__name='AGENT')
        district_summary = members.values('district__name').annotate(dc=Count('id'))

        cooperative_contribution = CooperativeContribution.objects.all().order_by('-update_date')[:5]
        cooperative_shares = CooperativeShareTransaction.objects.all().order_by('-update_date')
        product_price = ProductVariationPrice.objects.all().order_by('-update_date')
        collections = Collection.objects.all().order_by('-update_date')
        payments = MemberPaymentTransaction.objects.all().order_by('-transaction_date')
        success_payments = payments.filter(status='SUCCESSFUL')
        training = TrainingSession.objects.all().order_by('-create_date')
        # supply_requests = MemberSupplyRequest.objects.all().order_by('-create_date')
        # supply_requests = supply_requests.filter(status='ACCEPTED')
        m_shares = CooperativeMemberSharesLog.objects
        messages = OutgoingMessages.objects.all()
        if not self.request.user.profile.is_union():
            if hasattr(self.request.user, 'cooperative_admin'):
                coop_admin = self.request.user.cooperative_admin.cooperative
                cooperatives = cooperatives.filter(pk=coop_admin.id)
                members = members.filter(cooperative=coop_admin)
                cooperative_shares = cooperative_shares.filter(cooperative=coop_admin)
                m_shares = m_shares.filter(cooperative_member__cooperative=coop_admin)
                collections = collections.filter(member__cooperative=coop_admin)
                district_summary = district_summary.filter(cooperative=coop_admin)
        collection_qty = collections.aggregate(total_amount=Sum('quantity'))
        total_payment = success_payments.aggregate(total_amount=Sum('amount'))
        collection_amt = collections.aggregate(total_amount=Sum('total_price'))
        members_shares = members.aggregate(total_amount=Sum('shares'))
        male = members.filter(Q(gender__iexact='male') | Q(gender='m'))
        female = members.filter(Q(gender__iexact='female') | Q(gender='f'))
        is_refugee = members.filter(is_refugee=True)
        is_handicap = members.filter(is_handicap=True)
        teeyouthmale = [m.age_ for m in male if 18 <= m.age_ <= 34]#m.age_ >= 18 and m.age_ <= 34]
        teeyouthf = [f.age_ for f in female if 18 <= f.age_ <= 34 ]#m.age_ >= 18 and f.age_ <= 34]
        adultmale = [m.age_ for m in male if m.age_ >= 35]
        adultfemale = [f.age_ for f in female if f.age_ >= 35]
        below18 = [mem.age_ for mem in members if mem.age_ < 18]

        # print(teeyouthmale)
        # print(teeyouthf)
        # print(adultmale)
        # print(adultfemale)
        # print(below18)

        # members_animals = members.aggregate(total_amount=Sum('animal_count'))
        shares = cooperatives.aggregate(total_amount=Sum('shares'))
        m_shares = m_shares.values('cooperative_member',
                                   name=Concat('cooperative_member__surname',
                                               V(' '),
                                               'cooperative_member__first_name'
                                               ),

                                   ).annotate(total_amount=Sum('amount'), total_shares=Sum('shares'),
                                              transaction_date=Max('transaction_date')).order_by('-transaction_date')

        cooperative_shares = cooperative_shares.values('cooperative',
                                                       'cooperative__name',
                                                       ).annotate(total_amount=Sum('amount_paid'),
                                                                  total_shares=Sum('shares_bought'),
                                                                  transaction_date=Max('transaction_date')).order_by('-transaction_date')

        context['clans'] = clans.count()
        context['cooperatives'] = cooperatives.count()
        context['suppliers'] = suppliers.count()
        context['orders'] = orders.count()
        context['loans'] = loans.count()
        context['agents'] = agents.count()
        context['sum_loans'] = sum_loans
        context['coop_summary'] = cooperatives
        context['district_summary'] = district_summary

        context['shares'] = shares['total_amount']
        context['transactions'] = Cooperative.objects.all().count()
        context['members'] = members.count()
        context['male'] = male.count()
        context['female'] = female.count()
        context['is_refugee'] = is_refugee.count()
        context['is_handicap'] = is_handicap.count()

        context['teeyouthmale'] = len(teeyouthmale)
        context['teeyouthf'] = len(teeyouthf)
        context['adultmale'] = len(adultmale)
        context['adultfemale'] = len(adultfemale)
        context['below18'] = len(below18)

        context['active'] = ['_dashboard', '']
        context['members_shares'] = members_shares['total_amount']
        context['m_shares'] = m_shares[:5]
        context['collections_latest'] = collections[:5]
        context['collections'] = collection_qty['total_amount']
        context['collection_amt'] = collection_amt['total_amount']
        context['total_payment'] = total_payment['total_amount']

        context['cooperative_contribution'] = cooperative_contribution
        context['cooperative_shares'] = cooperative_shares[:5]
        context['training'] = training[:5]
        context['product_price'] = product_price
        context['sms'] = messages.filter(status='SENT').count()
        # context['supply_requests'] = supply_requests[:5]
        return context


class TerritoryDashboardView(TemplateView):
    template_name = "te_dashboard.html"

    def get_context_data(self, **kwargs):
        agent_array = []
        te_array = []
        context = super(TerritoryDashboardView, self).get_context_data()
        tes = Profile.objects.filter(access_level__name="TERRITORY")
        agents = Profile.objects.filter(access_level__name="AGENT")

        for agent in agents:
            members = CooperativeMember.objects.filter(create_by=agent.user)
            total_profile = members.count()
            # carded = members.filter(Q(consumer_device_id__isnull=False)|Q(consumer_device_id="")|Q(consumer_device_id="null"))
            carded = members.exclude(Q(consumer_device_id="")|Q(consumer_device_id="null"))
            wallet = members.filter(create_wallet=True)
            ids = members.filter(id_number__isnull=False)
            agent_array.append(
                {"agent_name": agent.user.get_full_name(), "total_profile":total_profile, "carded": carded.count(), "wallet": wallet.count(), "with_id": ids.count() }
            )

        for te in tes:
            agents = Profile.objects.values_list('user__id', flat=True).filter(access_level__name="AGENT", supervisor=te.user)
            members = CooperativeMember.objects.filter(create_by__in=agents)
            total_profile = members.count()
            carded = members.exclude(Q(consumer_device_id="")|Q(consumer_device_id="null"))
            wallet = members.filter(create_wallet=True)
            ids = members.filter(id_number__isnull=False)
            te_array.append(
                {"te_name": te.user.get_full_name(), "total_profile":total_profile, "carded": carded.count(), "wallet": wallet.count(), "with_id": ids.count() }
            )

        agent_ordered_data = sorted(agent_array, key=lambda x: x['total_profile'], reverse=True)
        te_ordered_data = sorted(te_array, key=lambda x: x['total_profile'], reverse=True)

        months_choices = [(str(month), name) for month, name in MONTHS.items()]
        current_month = datetime.date.today().month

        members = CooperativeMember.objects.filter()
        total_profile = members.count()
        carded = members.exclude(Q(consumer_device_id="") | Q(consumer_device_id="null"))
        wallet = members.filter(create_wallet=True)
        ids = members.filter(id_number__isnull=False)

        context['months_choices'] = months_choices
        context['current_month'] = str(current_month)
        context['agents_stats'] = agent_ordered_data
        context['te_stats'] = te_ordered_data
        context['total_members'] = total_profile
        context['total_carded'] = carded.count()
        context['total_nin'] = ids.count()
        context['total_wallet'] = wallet.count()
        context['carding_percentage'] = (carded.count() / total_profile) * 100 if total_profile > 0 else  0
        context['active'] = ['_dashboard_te']
        return context


def get_profiles_by_te(request):
    te_data_array = ["Farmers"]
    te_carded_array = ["CardsIssued"]
    te_array = []
    tes = Profile.objects.filter(access_level__name="TERRITORY")
    for te in tes:
        agents = Profile.objects.values_list('user__id', flat=True).filter(access_level__name="AGENT",
                                                                           supervisor=te.user)
        members = CooperativeMember.objects.filter(create_by__in=agents)
        total_profile = members.count()
        carded = members.exclude(Q(consumer_device_id="") | Q(consumer_device_id="null"))
        wallet = members.filter(create_wallet=True)
        ids = members.filter(id_number__isnull=False)

        te_data_array.append(total_profile)
        te_carded_array.append(carded.count())
        te_array.append(te.user.username)

    return JsonResponse({"data": te_data_array, "carded": te_carded_array,  "tes": te_array})


def get_total_per_day(request):
    # Fetch all records
    month = request.GET.get('month')
    print(month)
    agents = Profile.objects.values_list('user__id', flat=True).filter(access_level__name="AGENT")
    # all_members = CooperativeMember.objects.filter(create_by__in=agents).order_by("id")
    all_members = CooperativeMember.objects.all().order_by("create_date")
    current_month = datetime.datetime.now().month
    # if month:
    #     all_members = CooperativeMember.objects.filter(create_date__month=month).order_by("-create_date")
    # Initialize a dictionary to store counts per day
    daily_counts = {}

    # Iterate through records and count per day
    for member in all_members:
        # Extract the date part of create_date
        print(member.create_date.date())
        # day = datetime(member.create_date.year, member.create_date.month, member.create_date.day).date()
        day = member.create_date.date()
        # Update the count for the day
        if day in daily_counts:
            daily_counts[day] += 1
        else:
            daily_counts[day] = 1
    result_list = ["Days"]
    # Convert the dictionary to a list of dictionaries
    for key, value in daily_counts.items():
        result_list.append(value)
    result_key_list = [key for key, value in daily_counts.items()]

    return JsonResponse({"days":result_list, "keys": result_key_list})


def get_total_per_day(request):
    result_list = ["Days"]
    result_key_list = []
    results = (
        CooperativeMember.objects
        .annotate(date=TruncDate('create_date'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    for result in results:
        result_list.append(result['count'])
        result_key_list.append(result['date'])
        
    return JsonResponse({"days": result_list, "keys": result_key_list})

