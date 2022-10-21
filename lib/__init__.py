"""
    Module: __INIT__.PY;
    Role: Main;
    Application: Mobile Broadband Automation Helper library;
    Build: PyPi
    Dist: Cross-Platform;
    Copyright (c) 2021 Exvous Cloud Services. All rights are reserved.
"""

import os
import requests
import time
import json
from datetime import datetime as dt
import xmltodict
from bs4 import BeautifulSoup

# Local Modules
from .endpoints import Get, Post
from .enc import get_login_payload, parse_mac_filter
from .session import Session
from .conf import config


# ---------------
#   HUAWEI MBB  |
# ---------------


class Huawei(Session):
    def __init__(
            self,
            username: str = config.USERNAME,
            password: str = config.PASSWORD,
            host: str = "http://192.168.8.1"
    ):
        self.host = host
        self.username = username
        self.password = password

        super().__init__()

        # Micro get requests
        # ------------------
        self.status = lambda: self.get(Get.STATUS)
        self.device_info = lambda: self.get(Get.DEVICE_INFO)
        self.sim_info = lambda: self.get(Get.SIM_INFO)
        self.notifications = lambda: self.get(Get.NOTIFICATIONS)
        self.get_traffic = lambda: self.get(Get.GET_TRAFFIC)
        self.dhcp_info = lambda: self.get(Get.DHCP_INFO)
        self.get_hosts = lambda: self.get(Get.GET_HOSTS)
        self.get_blacklist = lambda: self.get(Get.GET_BLACKLIST)
        self.get_month_stats = lambda: self.get(Get.GET_MONTH_STATS)
        self.get_data_switch = lambda: self.get(Get.GET_DATA_SWITCH)
        self.get_sms_send_status = lambda: self.get(Get.GET_SMS_SEND_STATUS)
        # ------------------

    def login(self):
        home = self.session.get(self.host + Get.HOME)
        soup = BeautifulSoup(home.text, "html.parser")
        self.csrf = soup.select("head meta[name*=csrf_token]")[0]["content"]

        # login
        payload = get_login_payload(self.csrf, self.username, self.password)
        res = self.post(Post.LOGIN, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def set_data_switch(self, state: bool):
        if state > 3:
            return False
        payload = self.xml({
            "request": {
                "dataswitch": str(int(state))
            }
        })
        res = self.post(Post.SET_DATA_SWITCH, headers=self.post_headers(), data=payload)
        if "OK" in json.dumps(res):
            return self.get_data_switch()
        return res

    def switch_network_mode(self, state: int):
        payload = self.xml({
            "request": {
                "NetworkMode": "0" + str(state),
                "NetworkBand": "3FFFFFFF",
                "LTEBand": "7FFFFFFFFFFFFFFF"
            }
        })
        res = self.post(Post.SWITCH_NETWORK_MODE, headers=self.post_headers(), data=payload)
        if "OK" in json.dumps(res):
            return self.get_data_switch()
        return res

    def clear_traffic(self):
        payload = self.xml({
            "request": {
                "ClearTraffic": "1"
            }
        })
        res = self.post(Post.CLEAR_TRAFFIC, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def reboot(self):
        payload = self.xml({
            "request": {
                "Control": "1"
            }
        })
        res = self.post(Post.REBOOT, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def get_sms(self, box: int = 1, count: int = config.MAX_MSGS, page_index: int = 1):
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
        return self.post(Post.GET_SMS, headers=self.post_headers(), data=payload)

    def send_sms(self, msisdn: int, text: str):
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
                "Date": dt.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })
        res = self.post(Post.SEND_SMS, headers=self.post_headers(), data=payload)
        if "error" in json.dumps(res):
            return res
        else:
            start_ts = time.time()
            while True:
                response = self.get_sms_send_status()
                valid = str(msisdn) is response["response"]["SucPhone"]
                failed = str(msisdn) is response["response"]["FailPhone"]
                if time.time() > start_ts + config.SMS_TIMEOUT or valid or failed:
                    res = response
                    break
                time.sleep(config.INTERVAL / 1000)
            return res

    def del_sms(self, index_list: list):
        payload = self.xml({
            "request": {
                "Index": index_list
            }
        })
        res = self.post(Post.DEL_SMS, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def del_all_sms(self, box: int = 1, count: int = config.MAX_MSGS, page_index: int = 1):
        msgs = self.get_sms(box, count, page_index)
        if "response" not in msgs or "Messages" not in msgs["response"]:
            return False
        if int(msgs["response"]["Count"]) < 1 or not msgs["response"]["Messages"]["Message"]:
            return None
        msgs = msgs["response"]["Messages"]["Message"] if int(msgs["response"]["Count"]) > 1 else [
            msgs["response"]["Messages"]["Message"]
        ]
        index_list = [
            msg["Index"] for msg in msgs
        ]
        return self.del_sms(index_list)

    def read_sms(self, index_list: list):
        payload = self.xml({
            "request": {
                "Index": index_list
            }
        })
        res = self.post(Post.READ_SMS, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def read_all_sms(self, box: int = 1, count: int = config.MAX_MSGS, page_index: int = 1):
        msgs = self.get_sms(box, count, page_index)
        if "response" not in msgs or "Messages" not in msgs["response"]:
            return False
        if int(msgs["response"]["Count"]) < 1 or not msgs["response"]["Messages"]["Message"]:
            return None
        msgs = msgs["response"]["Messages"]["Message"] if int(msgs["response"]["Count"]) > 1 else [
            msgs["response"]["Messages"]["Message"]
        ]
        index_list = [
            msg["Index"] for msg in msgs
        ]
        return self.read_sms(index_list)

    def ussd(self, code_list: list):
        bucket = []

        code_list = code_list if isinstance(code_list, list) else code_list.split(">") \
            if isinstance(code_list, str) else None
        if not code_list:
            raise ValueError("expecting argument[1] either list or string")

        for code in code_list:
            payload = self.xml({
                "request": {
                    "content": code,
                    "codeType": "CodeType",
                    "timeout": ""
                }
            })
            res = self.post(Post.USSD, headers=self.post_headers(), data=payload)
            if "error" in json.dumps(res):
                continue

            get_res = lambda: self.session.get(f"{self.host}{Get.GET_USSD}").text
            start_ts = time.time()
            while True:
                response = get_res()
                if time.time() > start_ts + config.USSD_TIMEOUT or "error" not in response:
                    bucket.append({
                        code: self.parse(response)
                    })
                    break
                time.sleep(config.INTERVAL / 1000)

        return bucket

    def __update_mac_filter(self, blacklist: list):
        payload = self.xml({
            "request": {
                "Ssids": {
                    "Ssid": dict(
                        {
                            "Index": "0",
                            "WifiMacFilterStatus": "2",
                        },
                        **{
                            k + str(i): d for i, v in enumerate(blacklist) for k, d in v.items()
                        }
                    )
                    }
                }
            }
        )
        res = self.post(Post.UPDATE_MAC_FILTER, headers=self.post_headers(), data=payload)
        return "OK" in json.dumps(res)

    def blacklist(self, mac: str, alias: str = "GhostUser" + str(int(time.time() * 1000))):
        blacklist = parse_mac_filter(self.get_blacklist())
        match = [
            i for i, d in enumerate(blacklist) if d["WifiMacFilterMac"] == mac
        ]
        if len(match) > 0:
            raise RuntimeError(f"mac address already blacklisted")

        available_slots = [
            i for i, d in enumerate(blacklist) if not d["WifiMacFilterMac"]
        ]
        if len(available_slots) < 1:
            raise RuntimeError(f"maximum number of devices already allocated")

        slot_id = available_slots[0]
        blacklist[slot_id] = {
            "WifiMacFilterMac": mac,
            "wifihostname": alias
        }
        return self.__update_mac_filter(blacklist)

    def whitelist(self, mac: str):
        blacklist = parse_mac_filter(self.get_blacklist())
        match = [
            i for i, d in enumerate(blacklist) if d["WifiMacFilterMac"] == mac
        ]
        if len(match) < 1:
            return None

        slot_id = match[0]
        blacklist[slot_id] = {
            "WifiMacFilterMac": None,
            "wifihostname": None
        }
        return self.__update_mac_filter(blacklist)
