import requests
import hashlib
import random
import string
import json
import datetime
import base64
from conf.utils import generate_numeric, log_debug


class FlexipayTransactionC:

    password = "k0YcV9XpORhR0EpZzulADhWb3QXbBbt6PIZtOG2Xi4uvqcCYtDgodzVD9+uF9GDe"
    clientid = "INST000163"
    reference = None
    url = "https://196.8.208.149:9007/flexipayws/v1.0/registration/api"

    def __init__(self):
        pass

    def encrypt_string(self, hash_string):
        sha_signature = hashlib.sha256(base64.b64encode(hash_string.encode())).hexdigest()
        return sha_signature

    # def generate_numeric(size=8, prefix=""):
    #     x = ''.join(random.choice(string.digits) for i in range(size))
    #     return '{}{}'.format(prefix, x)

    def pretty_print_POST(self, req):
        """
        At this point it is completely built and ready
        to be fired; it is "prepared".

        However pay attention at the formatting used in
        this function because it is programmed to be pretty
        printed and may differ from the actual request.
        """
        print('{}\n{}\r\n{}\r\n\r\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ))

    def registration(self, params, flexypay):
        # reference = generate_numeric()
        reference = params.get('reference')
        card_no = params.get('card_number')
        mobile_number = params.get('mobile_number')
        dob = params.get('dob')
        first_name = params.get('first_name')
        second_name = params.get('second_name')
        last_name = params.get('last_name')
        nin = params.get('nin')
        gender = params.get('gender')
        member_id = params.get('member_id')

        token = self.encrypt_string('%s|%s' % (reference, self.password))

        payload = {
            "RequestID": "%s" % reference,
            "Request_Time": "%s" % datetime.datetime.now().strftime('%Y/%d/%m %H:%M:%S'),
            "no_of_records": "1",
            "Client_ID": self.clientid,
            "Narrative": "Farmer registration, farmer id %s" % member_id,
            # "callback_url": "https://172.31.7.2:80/flexipay",
            "callback_url": "https://10.43.0.49:80/flexipay/confirm/",
            "customer_data": [
                {
                    "card_no": card_no,
                    "mobile_number": mobile_number,
                    "dob": dob,#"1972/18/08",
                    "first_name": first_name,
                    "second_name": second_name,
                    "last_name": last_name,
                    "nin": nin,
                    "gender": gender,
                    "occupation": "FARMER"
                }
            ]
        }
        flexypay.request = payload
        flexypay.save()

        headers = {
            'Client_ID': self.clientid,
            'Token': token,
            'password': self.password,
            'Content-Type': 'application/json'
        }

        return self._request(payload, headers)

    def _request(self, payload, headers):
        url = self.url

        print('url:', url),
        print('data:', json.dumps(payload))
        try:
            req = requests.post(url, headers=headers, json=payload, verify=False)
            # log_debug(self.pretty_print_POST(req))
            # log_debug('status:', req.status_code)
            # {"Status": "00", "StatusMessage": "Registration details has been received successfully"}
            log_debug(req.json())
            return req.json()
        except Exception as e:
            print(e)
            log_debug(e)
            return {"Status": "99", "StatusMessage": "Failed Error Occured %s" % e}


