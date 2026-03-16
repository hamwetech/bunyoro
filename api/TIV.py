import requests
import json
from django.db.models import Q, CharField, Max, Sum, Count, Value as V
from conf.utils import log_error, log_debug


class DataSender:
    def __init__(self):
        self.url = "https://rails.innovationvillage.co.ug/api/partner/farmers/register"

    def register(self, member):

        payload = [
                {
                    "date": member.create_date.strftime('%Y-%m-%d'),
                    "name": "%s %s" % (member.first_name, member.surname),
                    "phone_number": "",
                    "gender": member.gender,
                    "dob": member.date_of_birth.strftime('%Y-%m-%d'),
                    "marital_status": "NA",
                    "district": member.district.name if member.district else "",
                    "sub_county": member.sub_county.name if member.sub_county else "",
                    "parish": member.parish.name if member.parish else "",
                    "village": member.get_village() if member.village else "",
                    "group_name": member.farmer_group.name if member.farmer_group else "",
                    "group_role": member.coop_role,
                    "fpo_name": member.cooperative.name if member.cooperative else "",
                    "major_crops": member.product,
                    "r_id": member.cpk_rid,
                    "consumer_device_id": member.consumer_device_id
                }
            ]
        log_debug(payload)
        response = self.send_data(payload)
        log_debug(response)
        if response['status'] != "error":
            member.sent_to_tiv=True
            member.save()

    def send_data(self, payload):
        headers = {'Content-Type': 'application/json', 'apikey': 'Hamwe', 'apisecret': 'ad5294b9124ece8cb40081ffa644d3cefcc5d3404d43b0ce0049752e46c0'}
        try:
            response = requests.post(self.url, data=json.dumps(payload), headers=headers, verify=False)
            # response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

            log_debug("TIV Response: %s" % response.status_code)
            log_debug(response.text)
            if response.status_code != "200":
                return json.loads(response.text)
            return {"status": "error"}

        except requests.exceptions.RequestException as e:
            print(e)
            log_error()
            return {"status": "error"}
