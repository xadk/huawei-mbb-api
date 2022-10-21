"""
    Module: ENC.PY;
    Role: Encryption for REST MBB APIs;
    Application: Mobile Broadband Automation Helper library;
    Build: PyPi
    Dist: Cross-Platform;
    Copyright (c) 2021 Exvous Cloud Services. All rights are reserved.
"""

import xmltodict
import hashlib
import base64

# ----------------
#   LOGIN Payload
# ----------------


def get_login_payload(csrf: str, username: str, password: str):
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


#   Mac Filter Parser
# -------------------

def parse_mac_filter(res):
    bucket = dict()

    def is_num(n):
        try:
            int(n)
            return True
        except ValueError:
            return False

    res = {k: v for k, v in res["response"]["Ssids"]["Ssid"].items() if is_num(k[-1])}
    for k, v in res.items():
        if k[-1] in bucket:
            bucket[k[-1]][k[:-1]] = v
        else:
            bucket[k[-1]] = {k[:-1]: v}

    return [
      v for k, v in bucket.items()
    ]
