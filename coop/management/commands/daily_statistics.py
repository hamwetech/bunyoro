from django.core.management.base import BaseCommand, CommandError
import datetime
from django.utils import timezone
from django.db.models import Q, CharField, Max, Sum, Count, Value as V
from conf.utils import get_consontant_upper
from coop.models import Cooperative, CooperativeMember
from django.db.models.functions import TruncDate
from userprofile.models import Profile, Device, AssignedCards


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        agent_array = []
        te_array = []
        today = timezone.now().date()

        tes = Profile.objects.filter(access_level__name="TERRITORY")
        agents = Profile.objects.filter(access_level__name="AGENT")

        for agent in agents:
            members = CooperativeMember.objects.filter(create_by=agent.user)
            total_profile = members.count()
            # carded = members.filter(Q(consumer_device_id__isnull=False)|Q(consumer_device_id="")|Q(consumer_device_id="null"))
            carded = members.exclude(Q(consumer_device_id="") | Q(consumer_device_id="null"))
            wallet = members.filter(create_wallet=True)
            ids = members.filter(id_number__isnull=False)
            agent_array.append(
                {"agent_name": agent.user.get_full_name(), "total_profile": total_profile, "carded": carded.count(),
                 "wallet": wallet.count(), "with_id": ids.count()}
            )

        for te in tes:
            agents = Profile.objects.values_list('user__id', flat=True).filter(access_level__name="AGENT",
                                                                               supervisor=te.user)
            members = CooperativeMember.objects.filter(create_by__in=agents)
            total_profile = members.count()
            carded = members.exclude(Q(consumer_device_id="") | Q(consumer_device_id="null"))
            wallet = members.filter(create_wallet=True)
            ids = members.filter(id_number__isnull=False)
            te_array.append(
                {"te_name": te.user.get_full_name(), "total_profile": total_profile, "carded": carded.count(),
                 "wallet": wallet.count(), "with_id": ids.count()}
            )

        agent_ordered_data = sorted(agent_array, key=lambda x: x['total_profile'], reverse=True)
        te_ordered_data = sorted(te_array, key=lambda x: x['total_profile'], reverse=True)
        today_profiles = Profile.objects.annotate(count=Count('id')).filter(create_date__date=today)

        print(today)

