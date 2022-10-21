import os
import time
import json
import xmltodict
import requests
import hashlib
import base64
from bs4 import BeautifulSoup
from datetime import datetime as dt


class Self:
    host = "192.168.8.1"


self = Self()


HOST = "http://192.168.8.1"
HOME_ENDPOINT = f"{self.host}/html/home.html"
LOGIN_ENDPOINT = f"{self.host}/api/user/login"
USERNAME = "admin"
PASSWORD = "lambda"
MAX_MSGS = 50
INTERVAL = 100      # ms
USSD_TIMEOUT = 10   # seconds
SMS_TIMEOUT = 10    # seconds


def get_login_payload(csrf, username, password):
    sha256 = lambda s: hashlib.sha256(s.encode()).hexdigest()
    b64 = lambda s: base64.b64encode(s.encode())
    pwd_hash = sha256(password)
    psd = b64(sha256(username + b64(pwd_hash).decode() + csrf)).decode()
    payload = {
        "request": {
            "Username": username,
            "Password": psd,
            "password_type": "4"
        }
    }
    return xmltodict.unparse(payload)


class Huawei:
    def __init__(self, username: str, password: str, host="http://192.168.8.1"):
        self.host = host
        self.username = username
        self.password = password
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        self.post_headers = lambda h: {
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

        self.session = requests.Session()
        self.session.headers = self.headers
        self.csrf = None
        self.parse = lambda x: json.loads(json.dumps(xmltodict.parse(x)))
        self.xml = lambda j: xmltodict.unparse(j)

        # Micro get requests
        # ------------------
        self.status = lambda: self.parse(self.session.get(f"{self.host}/api/monitoring/status").text)
        self.device_info = lambda: self.parse(self.session.get(f"{self.host}/api/device/information").text)
        self.sim_info = lambda: self.parse(self.session.get(f"{self.host}/api/net/current-plmn").text)
        self.notifications = lambda: self.parse(self.session.get(f"{self.host}/api/monitoring/check-notifications").text)
        self.get_traffic = lambda: self.parse(self.session.get(f"{self.host}/api/monitoring/traffic-statistics").text)
        self.dhcp_info = lambda: self.parse(self.session.get(f"{self.host}/api/dhcp/settings").text)
        self.get_hosts = lambda: self.parse(self.session.get(f"{self.host}/api/wlan/host-list").text)
        self.get_blacklist = lambda: self.parse(self.session.get(f"{self.host}/api/wlan/multi-macfilter-settings").text)
        self.get_month_stats = lambda: self.parse(self.session.get(f"{self.host}/api/monitoring/month_statistics").text)
        self.get_data_switch = lambda: self.parse(self.session.get(f"{self.host}/api/dialup/mobile-dataswitch").text)
        self.get_sms_send_status = lambda: self.parse(self.session.get(f"{self.host}/api/sms/send-status").text)
        # ------------------

    def login(self):
        home = self.session.get(HOME_ENDPOINT)
        soup = BeautifulSoup(home.text, "html.parser")
        self.csrf = soup.select("head meta[name*=csrf_token]")[0]["content"]

        # login
        payload = get_login_payload(self.csrf, self.username, self.password)
        login_headers = self.post_headers({
            "referrer": HOME_ENDPOINT
        })
        res = self.session.post(LOGIN_ENDPOINT, headers=login_headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return "OK" in res.text

    def set_data_switch(self, state: bool):
        if state > 3:
            return False
        headers = self.post_headers({
            "referrer": f"{self.host}/html/smsinbox.html",
        })
        payload = self.xml({
            "request": {
                "dataswitch": str(int(state))
            }
        })
        res = self.session.post(f"{self.host}/api/dialup/mobile-dataswitch", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]

        if "OK" in res.text:
            return self.get_data_switch()

        return self.parse(res.text)

    def switch_network_mode(self, state: int):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/mobilenetworksettings.html",
        })
        payload = self.xml({
            "request": {
                "NetworkMode": "0" + str(state),
                "NetworkBand": "3FFFFFFF",
                "LTEBand": "7FFFFFFFFFFFFFFF"
            }
        })
        res = self.session.post(f"{self.host}/api/net/net-mode", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]

        if "OK" in res.text:
            return self.get_data_switch()

        return self.parse(res.text)

    def clear_traffic(self):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/statistic.html",
        })
        payload = self.xml({
            "request": {
                "ClearTraffic": "1"
            }
        })
        res = self.session.post(f"{self.host}/api/monitoring/clear-traffic", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return self.parse(res.text)

    def reboot(self):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/reboot.html",
        })
        payload = self.xml({
            "request": {
                "Control": "1"
            }
        })
        res = self.session.post(f"{self.host}/api/device/control", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return self.parse(res.text)

    def get_sms(self, box: int = 1, count: int = MAX_MSGS, page_index: int = 1):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/smsinbox.html",
        })
        payload = self.xml({
            "request": {
                "PageIndex": str(page_index),
                "ReadCount": str(count),
                "BoxType": str(box),
                "SortType": "0",
                "Ascending": "0",
                "UnreadPreferred": "0"
            }
        })
        res = self.session.post(f"{self.host}/api/sms/sms-list", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return self.parse(res.text)

    def send_sms(self, msisdn: int, text: str):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/smsinbox.html",
        })
        payload = self.xml({
            "request": {
                "Index": "-1",
                "Phones": {
                    "Phone": str(msisdn)
                },
                "Sca": "",
                "Content": text,
                "Length": len(text),
                "Reserved": "1",
                "Date": "2021-03-04 14:24:48"
            }
        })
        res = self.session.post(f"{self.host}/api/sms/send-sms", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        if "error" in res.text:
            return self.parse(res.text)
        else:
            start_ts = time.time()
            while True:
                response = self.get_sms_send_status()
                valid = str(msisdn) is response["response"]["SucPhone"]
                failed = str(msisdn) is response["response"]["FailPhone"]
                if time.time() > start_ts + SMS_TIMEOUT or valid or failed:
                    res = response
                    break
                time.sleep(INTERVAL / 1000)
            return res

    def del_sms(self, index_list: list):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/smsinbox.html",
        })
        payload = self.xml({
            "request": {
                "Index": index_list
            }
        })
        res = self.session.post(f"{self.host}/api/sms/delete-sms", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return self.parse(res.text)

    def del_all_sms(self, box: int = 1, count: int = MAX_MSGS, page_index: int = 1):
        index_list = [
            msg["Index"] for msg in self.get_sms(box, count, page_index)
        ]
        return self.del_sms(index_list)

    def read_sms(self, index_list: list):
        headers = self.post_headers({
            "referrer": f"{self.host}/html/smsinbox.html",
        })
        payload = self.xml({
            "request": {
                "Index": index_list
            }
        })
        res = self.session.post(f"{self.host}/api/sms/set-read", headers=headers, data=payload)
        self.csrf = res.headers["__RequestVerificationToken"]
        return self.parse(res.text)

    def read_all_sms(self, box: int = 1, count: int = MAX_MSGS, page_index: int = 1):
        index_list = [
            msg["Index"] for msg in self.get_sms(box, count, page_index)
        ]
        return self.read_sms(index_list)

    def ussd(self, code_list: str):
        bucket = []
        code_list = code_list.split(">")
        for code in code_list:
            headers = self.post_headers({
                "referrer": f"{self.host}/html/smsinbox.html",
            })
            payload = self.xml({
                "request": {
                    "content": code,
                    "codeType": "CodeType",
                    "timeout": ""
                }
            })
            res = self.session.post(f"{self.host}/api/ussd/send", headers=headers, data=payload)
            self.csrf = res.headers["__RequestVerificationToken"]

            if "error" in res.text:
                continue

            get_res = lambda: self.session.get(f"{self.host}/api/ussd/get").text
            start_ts = time.time()
            while True:
                response = get_res()
                if time.time() > start_ts + USSD_TIMEOUT or "error" not in response:
                    bucket.append({
                        code: self.parse(response)
                    })
                    break
                time.sleep(INTERVAL / 1000)

        return bucket


modem = Huawei(HOST, USERNAME, PASSWORD)
if modem.login():
    print(json.dumps(modem.get_sms(1), indent=4))
    # print(json.dumps(modem.get_traffic(), indent=4))
    # print(json.dumps(modem.ussd("*911#"), indent=4))
    # print(json.dumps(modem.set_data_switch(True), indent=4))
    # print(json.dumps(modem.reboot(), indent=4))

else:
    print("UNAUTHORIZED")
