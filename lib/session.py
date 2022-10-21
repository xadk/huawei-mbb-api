"""
    Module: SESSION.PY;
    Role: Request Sessions;
    Application: Mobile Broadband Automation Helper library;
    Build: PyPi
    Dist: Cross-Platform;
    Copyright (c) 2021 Exvous Cloud Services. All rights are reserved.
"""

import requests
import json
import xmltodict

# ------------
#   SESSION
# ------------


class Session:
    def __init__(self):

        #   Headers
        # ------------
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        self.post_headers = lambda h={}: {
            **{
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "__RequestVerificationToken": self.csrf,
                "X-Requested-With": "XMLHttpRequest"
            },
            **h
        }

        #   Defaults
        # ------------

        self.session = requests.Session()
        self.session.headers = self.headers
        self.csrf = None
        self.parse = lambda x: json.loads(json.dumps(xmltodict.parse(x)))
        self.xml = lambda j: xmltodict.unparse(j)

        #   Requests
        # ------------
        self.get = lambda endpoint: self.parse(self.session.get(f"{self.host}{endpoint}").text)

        def __post(this, endpoint, **kwargs):
            res = this.session.post(f"{self.host}{endpoint}", **kwargs)
            if "__RequestVerificationToken" in res.headers:
                this.csrf = res.headers["__RequestVerificationToken"]
            return this.parse(res.text)

        self.post = lambda endpoint, **kwargs: __post(self, endpoint, **kwargs)
        # ------------
