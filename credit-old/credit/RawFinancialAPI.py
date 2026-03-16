import json
import hashlib
import requests
import base64
from datetime import datetime
from django.conf import settings
from conf.utils import log_debug, log_error


class RawFinancial:
    username = None
    password = None
    token = None
    url = None

    def __init__(self):
        self.username = "jasiimwe160@gmail.com"
        self.password = "trinity123!@#"
        self.url = "https://rawfinancial.fund/api/authentication/login"
        self.login()


    def login(self):
        try:
            payload = {
                "username": self.username,
                "password": self.password
            }
            req = requests.post(self.url, data=payload)
            log_debug("Login Response From Server %s" % req.text)
            jr = json.loads(req.text)
            self.token =  jr['token']
        except Exception as e:
            result = {"error": True, "response": "System Error during MM %s Request."}
            log_debug(e)

    def reg_trust_network(self, name):
        log_debug("Creating Trust Network")
        self.url = "https://rawfinancial.fund/trust_network/api/trust_network/"
        try:
            payload = {
                "channel": 1,
                "Name": name,
                "Description": "%s Hamwe API" % name
            }
            req = self.make_request(payload)
            return req
        except Exception as e:
            result = {"error": True, "response": "System Error during MM %s Request."}
            log_debug(e)
            return result

    def register_borrower(self, params):
        try:
            self.url = "https://rawfinancial.fund/borrowers/api/borrowers/"
            trust_network = params.get("trust_network")
            first_name = params.get("first_name")
            last_name = params.get("last_name")
            phone_number = params.get("phone_number")
            nin = params.get("nin")
            channel_borrower_uid = params.get("borrower_id")

            payload = {
                "tn": trust_network,
                "channel_borrower_uid":channel_borrower_uid,
                "first_name":first_name,
                "last_name":last_name,
                "phone_number":phone_number,
                "nin":nin,
                "email":"tech@hamwe.org",
                "address":"Address"
            }
            req = self.make_request(payload)
            return req
        except Exception as e:
            result = {"error": True, "response": "System Error during MM %s Request."}
            log_debug(e)
            return result

    def loan_request(self, params):
        try:
            self.url = "https://rawfinancial.fund/loans/api/loan_request/"
            channel_borrower_uid = params.get("channel_borrower_uid")
            amount = "%s" % params.get("loan_amount")
            loan_purpose = params.get("loan_purpose")
            loan_duration = params.get("loan_duration")

            payload = {
                "channel_borrower_uid":channel_borrower_uid,
                "channel_id": 1,
                "loan_amount": amount,
                "loan_purpose": loan_purpose,
                "loan_duration": loan_duration #Integer
            }
            req = self.make_request(payload)
            return req
        except Exception as e:
            result = {"error": True, "response": "System Error during MM %s Request."}
            log_debug(e)
            return result


    def loan_status(self, reference):
        self.url = "https://rawfinancial.fund/loans/api/loan_status/%s/" % reference
        try:
            headers = {'content-type': 'application/json', 'Authorization': 'Token %s' % self.token}
            log_debug(headers)
            log_debug(self.url)
            req = requests.get(self.url, headers=headers)
            log_debug("Loan Status Response From Server %s" % req.text)
            jr = json.loads(req.text)
            return jr
        except Exception as e:
            result = {"transactionStatus": "INDETERMINATE", "response": "System Error during MM %s Request." % e,
                      "reference_code": None, "error": True}
            log_debug(e)
            return result


    def make_request(self, payload):
        reference_code = None
        try:
            headers = {'content-type': 'application/json', 'Authorization': 'Token %s' % self.token}
            log_debug(headers)
            log_debug(payload)
            req = requests.post(self.url, data=json.dumps(payload), headers=headers)
            log_debug("Response From Server %s" % req.text)
            jr = json.loads(req.text)
            return jr
        except Exception as e:
            result = {"transactionStatus": "INDETERMINATE", "message": "System Error during MM %s Request." % e,
                      "reference_code": None, "error": True}
            log_debug(e)
            return result
