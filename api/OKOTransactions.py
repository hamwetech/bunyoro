import requests
import json
from datetime import datetime
class OKOTransaction():
    # baseUrl = 'https://okotestjorge.azurewebsites.net/api'
    baseUrl = 'https://okoops.com/api'

    def __init__(self):
        pass

    def CreatePolicyPartner(self, params):
        return self._request("/policy/CreatePolicyPartner", params)

    def ChecckPolicy(self, policy_id):
        import time
        # time.sleep(10)
        return self._requestGET("/Policy/RequestPolicyStatus?policyId=%s" % policy_id)

    def _request(self, endpoint, payload):
        url = self.baseUrl + endpoint

        print('url:', url),
        print('data:', json.dumps(payload))

        req = requests.post(url, json=payload)
        print('status:', req.status_code)
        print(req.json())

        return req.json()

    def _requestGET(self, endpoint):
        url = self.baseUrl + endpoint
        print('url:', url),
        req = requests.get(url)
        print('status:', req.status_code)
        print(req.json())
        return req.json()