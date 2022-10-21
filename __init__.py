import os
import sys
import types
import netifaces
import time
import json
import inspect
import shutil
import argparse
import textwrap
from urllib.parse import urlparse, ParseResult

from lib import Huawei


# No  __pyache__
sys.dont_write_bytecode = True


class NotAuthorizedException(BaseException):
    """Unauthorized: please check username & password"""


def get_default_gateway_ip():
    gateways = netifaces.gateways()
    try:
        return gateways['default'][netifaces.AF_INET][0]
    except:
        print("Error: Not connected to the modem")
        sys.exit(1)


def humansize(nbytes: int):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def hms(s: int):
    return time.strftime('%H:%M:%S', time.gmtime(s))


def convert_values(k: str, v: any):
    try:
        if k.endswith("Upload") or k.endswith("Download") or k.endswith("UploadRate") or k.endswith("DownloadRate"):
            v = humansize(int(v))
        elif k.endswith("Time") or k.endswith("MonthDuration"):
            v = hms(int(v))
    except:
        pass
    finally:
        return v


# Function for flattening JSON
def flatten_json(y: any, chain_names: bool = True):
    bucket = []
    idx = 0

    def flatten(x: any, name: str = ""):
        nonlocal bucket, idx
        if len(bucket) <= idx:
            bucket.append(dict())
        # If the Nested key-value
        # pair is of dict type
        if type(x) is dict:
            idx += 1
            for a in x:
                flatten(x[a], name + a + '.' if chain_names else a)

        # If the Nested key-value
        # pair is of list type
        elif type(x) is list:
            idx += 1
            i = 0
            for a in x:
                if name[-1] == ".":
                    name = name[:-1]
                flatten(a, f"{name}[{str(i)}]." if chain_names else "")
                i += 1
        else:
            bucket[idx][name[:-1] if chain_names else name] = x

    flatten(y)
    # removes empty objs
    return [x for x in bucket if x]


def pretty_print(cmd_title: str, data: any):
    cols = shutil.get_terminal_size().columns - 8
    kl = int(cols / 3)
    vl = cols - kl
    lx = kl + vl

    header_type = 1
    match header_type:
        case 0:
            print(f"+%{lx + 6}s+\n| %{lx + 4}s |\n+%{lx + 6}s+" % (
                (lx + 6) * "—", cmd_title.title().center(lx + 4), (lx + 6) * "—"))
        case 1:
            l = len(cmd_title.title())
            ml = 10
            print(f"\n+%s༺   %{l}s ༻ %s+" % (
                "─" * int(((lx - l) * ml - 4) / 100),
                cmd_title.title(),
                "─" * int(((lx - l) * (100 - ml) - 3) / 100),
            ))

    pt = lambda d, klx, vlx: [
        print("".join(
            [
                "\n".join([f"|   %-{klx}s %-{vlx}s" % (
                    "..." + k[-(klx - 3):] if len(k) > klx else k,
                    "".join([
                        (
                            "\n|" + (" " * (klx + 4)) + line if i > 0 else line
                        ) + " " * (vlx - len(line) + 2) + "|"
                        for i, line in enumerate([
                            spline.strip() for pline in
                            convert_values(k, str(v)).strip().split("\n")
                            for spline in textwrap.fill(
                                pline,
                                width=vlx - 2,
                            ).split("\n")
                        ])
                    ])
                ) for k, v in o.items()]) + (
                        "\n|   " + ("—" * (klx + vlx)) + "   |\n"
                ) for i, o in enumerate(flatten_json(d, False))
            ]
        )[:-(klx + vlx + 10)])  # -(last line offset + 8 from col + 2 \n\n)
    ]

    try:
        pt(data['response'] if isinstance(data, dict) and 'response' in data
           else data if isinstance(data, dict) else dict(Response=data),
           kl, vl)
        print(f"+%{lx + 6}s+" % ((lx + 6) * "—"))

    except Exception as e:
        print("Error:", "\n".join([str(s) for s in e.args]))
        sys.exit(1)


if __name__ == "__main__":

    # default gateway
    default_gateway_ip = get_default_gateway_ip()

    # Parser
    parser = argparse.ArgumentParser(
        prog="",
        description="APIs for Huawei Mobile Broadband Devices (MBBs)",
    )

    # ------------
    #  Core args |
    # ------------

    parser.add_argument(
        "-g",
        "--default_gateway",
        type=str,
        # metavar="Gateway",
        nargs=1,
        default=default_gateway_ip,
        help=f"gateway ip address (i.e. 192.168.XX.XX) [default={default_gateway_ip} (from WiFi)]"
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        # metavar="Username",
        nargs="?",
        const="admin",
        default="admin",
        help="username for modem gateway (default=admin)"
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        # metavar="Password",
        nargs="?",
        const="admin",
        default="admin",
        help="password for modem gateway (default=admin)"
    )

    # ------------------
    #  No args cmdlets |
    # ------------------

    parser.add_argument(
        "-s",
        "--status",
        dest="status",
        action="store_true",
        help="get device status"
    )
    parser.add_argument(
        "-i",
        "--info",
        dest="device_info",
        action="store_true",
        help="get device info"
    )
    parser.add_argument(
        "-r",
        "--reboot",
        dest="reboot",
        action="store_true",
        help="reboot the device"
    )
    parser.add_argument(
        "-n",
        "--notifications",
        dest="notifications",
        action="store_true",
        help="get notifications"
    )
    parser.add_argument(
        "-t",
        "--traffic-usage",
        dest="get_traffic",
        action="store_true",
        help="get traffic usage"
    )
    parser.add_argument(
        "-l",
        "--list-devices",
        dest="get_hosts",
        action="store_true",
        help="lists connected devices"
    )
    parser.add_argument(
        "-sim",
        "--sim-info",
        dest="sim_info",
        action="store_true",
        help="get sim info"
    )
    parser.add_argument(
        "-dhcp",
        "--dhcp-info",
        dest="dhcp_info",
        action="store_true",
        help="get dhcp info"
    )
    parser.add_argument(
        "-qt",
        "--clear-traffic",
        dest="clear_traffic",
        action="store_true",
        help="clear traffic usage"
    )
    parser.add_argument(
        "-lb",
        "--list-blacklist",
        dest="get_blacklist",
        action="store_true",
        help="lists blacklisted devices"
    )
    parser.add_argument(
        "-lu",
        "--stat-data-usage",
        dest="get_month_stats",
        action="store_true",
        help="stat data usage"
    )
    parser.add_argument(
        "-ld",
        "--stat-data-switch",
        dest="get_data_switch",
        action="store_true",
        help="stat data switch"
    )
    parser.add_argument(
        "-ls",
        "--stat-sms-send-status",
        dest="get_sms_send_status",
        action="store_true",
        help="stat sms send status"
    )

    # ------------------
    #  Args w/ cmdlets |
    # ------------------

    parser.add_argument(
        "-d",
        "--dial",
        dest="ussd",
        nargs="+",
        type=str,
        help="dial a ussd code"
    )
    parser.add_argument(
        "-yd",
        "--toggle-data",
        dest="set_data_switch",
        metavar="INT",
        nargs=1,
        type=int,
        help="toggle data switch: args = (0|1)"
    )
    parser.add_argument(
        "-ym",
        "--switch-net-mode",
        dest="switch_network_mode",
        metavar="INT",
        nargs=1,
        type=int,
        help="switch network mode: args = [1 = 2G, 2 = 3G, 3 = LTE]"
    )
    parser.add_argument(
        "-a",
        "--get-messages",
        dest="get_sms",
        metavar="OPTION",
        nargs="+",
        type=int,
        help="retrieve sms: args = (box, count, page_index)"
    )
    parser.add_argument(
        "-rm",
        "--del-message",
        dest="del_sms",
        metavar="INDEX",
        nargs="+",
        type=int,
        help="delete sms: args = [index_list...]"
    )
    parser.add_argument(
        "-rf",
        "--del-all-messages",
        dest="del_all_sms",
        metavar="OPTION",
        nargs="+",
        type=int,
        help="delete all sms: args: (box, count, page_index)"
    )
    parser.add_argument(
        "-qm",
        "--read-message",
        dest="read_sms",
        metavar="INDEX",
        nargs="+",
        type=int,
        help="mark an sms as read: args = [index_list...]"
    )
    parser.add_argument(
        "-qa",
        "--read-all-messages",
        dest="read_all_sms",
        metavar="OPTION",
        nargs="+",
        type=int,
        help="mark all sms as read: args = (box, count, page_index)"
    )
    parser.add_argument(
        "-b",
        "--blacklist",
        dest="blacklist",
        metavar="mac_address, alias",
        nargs="+",
        type=str,
        help="blacklist device(s): args = (mac_address, alias)"
    )
    parser.add_argument(
        "-w",
        "--whitelist",
        dest="whitelist",
        metavar="mac_address",
        nargs=1,
        type=str,
        help="whitelist device(s)"
    )

    # ------------------
    #  Sub cmd parsers |
    # ------------------

    subparsers = parser.add_subparsers(required=False)

    # Message sub-parser
    msg_parser = subparsers.add_parser("msg", help='send a message')
    msg_parser.add_argument(
        '-p', '--phone',
        dest="msg_phone_numbers",
        type=int,
        metavar="PHONE",
        nargs="+",
        action="extend",
        help="phone number(s)",
        required=True
    )
    msg_parser.add_argument(
        '-t', '--text',
        dest="msg_text",
        type=str,
        metavar="TEXT",
        help="message content",
        required=True
    )

    # -------------------
    #  Initializing cls |
    # -------------------

    args = parser.parse_args()
    # print(args, "\n\n")

    try:
        modem = Huawei(
            username=args.username,
            password=args.password,
            host=f"http://{args.default_gateway}"
        )
        if not modem.login():
            raise NotAuthorizedException("incorrect username or password!")
    except Exception as e:
        print("Error:", "\n".join([str(s) for s in e.args]))
        sys.exit(1)

    """
        ------ looping through args ---------
        | individual arg calls a method     |
        | from the main class w/ or without |
        | the argument values of each cmd   |
        -------------------------------------
    """
    for arg in [i for i in args.__dict__.keys() if i[:1] != '_']:
        # ----------------------------------
        #  Cmds w/ calls to exposed method |
        # ----------------------------------
        if hasattr(modem, arg) and len([
            t for t in [types.FunctionType, types.MethodType, types.LambdaType]
            if isinstance(getattr(modem, arg), t)
        ]) > 0:
            arg_val = getattr(args, arg)
            call = getattr(modem, arg)
            res = None

            # get fxn no args
            if isinstance(arg_val, bool):
                if arg_val:
                    res = call()

            # with args
            elif arg_val:
                res = call(*(
                    [arg_val]  # for common *arg ^
                    if len(inspect.getfullargspec(call).args) > 1 and list(
                        inspect.getfullargspec(call).annotations.values()
                    )[0] == list
                    else arg_val[:len(inspect.getfullargspec(call).args) - 1]  # -1 for self
                ) if isinstance(arg_val, list) else arg_val)
                res = dict(Returned=res)  # for pretty table

            # customized fxn
            else:
                pass
            if not res:
                continue

            # pretty printing table
            pretty_print(
                arg,
                res
            )

    # ---------------------------
    #  Custom / Sub-parsed cmds |
    # ---------------------------

    if hasattr(args, "msg_phone_numbers") and len(args.msg_phone_numbers) > 0 and args.msg_text:
        send_msg_responses = []
        for msisdn in args.msg_phone_numbers:
            send_msg_res = modem.send_sms(msisdn, args.msg_text)
            send_msg_responses.append(send_msg_res)
        pretty_print(
            "SMS",
            send_msg_responses
        )
