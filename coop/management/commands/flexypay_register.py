from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from conf.utils import internationalize_number
from coop.models import CooperativeMember, FlexiPayTransaction
from api.Fexipay import FlexipayTransactionC

from conf.utils import log_error, log_debug, generate_numeric


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        members = CooperativeMember.objects.filter(create_wallet=True, has_flexipay=False)
        for member in members:
            try:
                reference = generate_numeric()
                with transaction.atomic():
                    payload = {
                        "reference": reference,
                        "member_id": member.member_id,
                        "last_name": member.surname,
                        "first_name": member.first_name,
                        "second_name": member.other_name if member.other_name else "",
                        "gender": member.gender,
                        "card_number": member.card_number,
                        "nin": member.id_number,
                        "dob": member.date_of_birth.strftime('%Y/%m/%d') if member.date_of_birth else "",
                        "mobile_number": member.phone_number if member.phone_number else "",
                        # "mobile_number": member.phone_number.replace("256", "") if member.phone_number else "",
                    }

                    flexypay = FlexiPayTransaction.objects.create(
                        cooperative_member=member,
                        reference=reference
                    )
                    log_debug("Flexipay Transaction Initiated: Payload %s" % payload)
                    flx = FlexipayTransactionC()
                    res = flx.registration(payload, flexypay)
                    log_debug("Flexipay Transaction Response: %s" % res)

                    flexypay.response = res
                    flexypay.save()
                    if res:
                        if res['Status'] == "00":
                            member.has_flexipay = True
                            member.save()
            except Exception as e:
                log_error()
                print('not registered to flexipay %s' % e)