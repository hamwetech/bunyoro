import json
import hashlib
import requests
import base64
from datetime import datetime
from django.conf import settings
from conf.utils import log_debug, log_error


class HamwePay:
    accountid = None
    password = None
    http_auth = None
    timestamp = None
    token = None
    url = None

    def __init__(self, credentials):
        self.accountid = credentials.get('accountid')
        self.password = credentials.get('password')
        self.http_auth = base64.urlsafe_b64encode(credentials.get('http_credentials'))
        self.timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        self.token = base64.urlsafe_b64encode(self.accountid + self.password + self.timestamp)
        self.url = 'https://payments.hamwepay.com/endpoint/service/transaction/'
        self.status_url = self.url

    def mobile_money_transaction(self, params):
        try:
            data = {
                "reference": params.get('reference'),
                "method": params.get('method'),
                "amount": params.get('amount'),
                "timestamp": self.timestamp,
                "token": self.token,
                "phonenumber": params.get('phone_number'),
                "accountid": self.accountid
            }

            log_debug("Sending Transaction: %s" % data)

            return self.make_request(data)

        except Exception as err:
            log_error()
            return {"status": "ERROR", "statusMessage": "Server Error"}

    def check_status(self, reference):
        self.url = "%s%s" % (self.status_url, reference)
        payload = {}
        request = self.make_request(payload)

        if not request:
            return {
                "status": "FAILED",
                "message": "System Failure. Contact Admin"
            }
        return request  # {'status': u'SUCCESSFUL', 'message': None, 'reference_code': reference_code} #request

    def check_balance(self, msisdn, _type):
        payload = {
            "username": self.username,
            "password": self.password,
            "api": "checkmsisdnnetworkbalance",
            "msisdn": msisdn,
            "type": _type
        }
        request = self.make_request(payload)

        if not request:
            return {
                "status": "FAILED",
                "message": "System Failure. Contact Admin"
            }
        return request

    def make_request(self, payload):
        reference_code = None
        try:
            headers = {'content-type': 'application/json', 'Authorization': 'Basic %s' % self.http_auth}
            log_debug(self.url)
            req = requests.post(self.url, data=json.dumps(payload), headers=headers)
            log_debug("Response From Server %s" % req.text)
            jr = json.loads(req.text)
            if 'transactionStatus' in jr:
                if jr['transactionStatus'] == 'SUCCESSFUL':
                    log_debug(jr)
            return jr
        except Exception as e:
            result = {"transactionStatus": "INDETERMINATE", "message": "System Error during MM %s Request." % e,
                      "reference_code": None, "error": True}
            log_debug(e)
            return result