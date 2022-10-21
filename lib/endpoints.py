"""
    Module: ENDPOINTS.PY;
    Role: Endpoints for REST MBB APIs;
    Application: Mobile Broadband Automation Helper library;
    Build: PyPi
    Dist: Cross-Platform;
    Copyright (c) 2021 Exvous Cloud Services. All rights are reserved.
"""

#  GET ENDPOINTS
# ---------------


class Get:
    HOME = f"/html/home.html"
    STATUS = "/api/monitoring/status"
    DEVICE_INFO = "/api/device/information"
    SIM_INFO = "/api/net/current-plmn"
    NOTIFICATIONS = "/api/monitoring/check-notifications"
    GET_TRAFFIC = "/api/monitoring/traffic-statistics"
    DHCP_INFO = "/api/dhcp/settings"
    GET_HOSTS = "/api/wlan/host-list"
    GET_BLACKLIST = "/api/wlan/multi-macfilter-settings"
    GET_MONTH_STATS = "/api/monitoring/month_statistics"
    GET_DATA_SWITCH = "/api/dialup/mobile-dataswitch"
    GET_SMS_SEND_STATUS = "/api/sms/send-status"
    GET_USSD = "/api/ussd/get"


#  POST ENDPOINTS
# ----------------


class Post:
    LOGIN = "/api/user/login"
    SET_DATA_SWITCH = "/api/dialup/mobile-dataswitch"
    SWITCH_NETWORK_MODE = "/api/net/net-mode"
    CLEAR_TRAFFIC = "/api/monitoring/clear-traffic"
    REBOOT = "/api/device/control"
    GET_SMS = "/api/sms/sms-list"
    SEND_SMS = "/api/sms/send-sms"
    DEL_SMS = "/api/sms/delete-sms"
    READ_SMS = "/api/sms/set-read"
    USSD = "/api/ussd/send"
    UPDATE_MAC_FILTER = "/api/wlan/multi-macfilter-settings"
