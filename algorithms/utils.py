# 获取链上数据
import datetime
import json
import math
import random

import pytz
import requests

DECIMALS = 10
tz = pytz.timezone('Asia/Shanghai')


def get_data(method, params=None, wallet="t2"):
    return r(method, params, wallet, return_response=False)


def return_data(method, params=None, wallet="t2"):
    return r(method, params, wallet, return_response=True)


# 正常数据返回
def s(data):
    return {
        "error": 0,
        "data": data
    }


def r(method, params=None, wallet="t2", return_response=True, try_load=True):
    if params is None:
        params = []
    payload = {"jsonrpc": "1.0", "id": "curltest1", "method": method, "params": params}
    payload = json.dumps(payload)
    print("payload:", payload)
    url = f"http://127.0.0.1:18443/wallet/{wallet}"
    headers = {
        'Content-Type': 'text/plain',
        'Authorization': 'Basic Yml0Y29pbjpiaXRjb2lu',
    }
    err = 0
    data = []
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code != 200:
            try:
                response_data = response.json()
            except Exception as e:
                response_data = {}
            if try_load and response.status_code == 500 and response_data.get("error") and response_data["error"][
                "code"] == -18:
                err, data = r("loadwallet", [wallet], return_response=False, try_load=False)
                if err == 0:
                    return r(method, params, wallet, return_response, try_load=False)
                else:
                    err, data = response_data["error"]["code"], response_data["error"]
            elif response_data.get("error") is not None:
                err, data = response_data["error"]["code"], response_data["error"]
                print(F"请求错误({response.status_code}):", response.text)
            else:
                err, data = response.status_code, response.text
        else:
            try:
                response_data = response.json()
                print("response_data:", response_data)
                if response_data.get("error") is not None:
                    err, data = response_data["error"]["code"], response_data["error"]
                else:
                    err, data = 0, response_data["result"]
            except Exception as e:
                err, data = 499, str(e)
    except Exception as e:
        print("请求错误:", e)
        err, data = 500, str(e)
    if return_response:
        return {
            "error": err,
            "data": data
        }
    else:
        return err, data


def load_addresses():
    with open("./data/addresses.json", "r") as f:
        return json.loads(f.read())


# 向下取整保留指定位数小数
def floor(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier


def confirm(address):
    return get_data('generatetoaddress', [6, address], wallet="miner")


def get_balance(wallet):
    return get_data("getbalance", wallet=wallet)


def mock(wallet, amount):
    amount = int(amount * DECIMALS)
    wallet_id = int(wallet[1:])
    wallets = list(range(1, 11))
    wallets.remove(wallet_id)
    selected_ids = random.sample(wallets, random.randint(1, 5))
    data = {}
    data[wallet] = amount / DECIMALS

    for w in selected_ids:
        _, balance = get_balance(f"f{w}")
        b = int(DECIMALS * balance)
        if b > 100:
            b = 100
        a = 1
        if a >= b:
            continue
        c = random.randint(a, b)
        data[f"f{w}"] = c / DECIMALS
    return data


def now():
    return datetime.datetime.now().astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.datetime.now().astimezone(tz).strftime("%Y%m%d")


def log_process(replenished_data, c):
    data = {
        "replenished_data": replenished_data,
        "c": c
    }
    with open("./data/process_data.log", "a") as f:
        f.write(now() + "|" + json.dumps(data) + "\n")


def log_transfer(hex, json_data):
    with open("./data/transfer.log", "a") as f:
        f.write(now() + "|" + hex + "|" + json.dumps(json_data) + "\n")


def log_transfer_data(data):
    txid = data["txid"]
    with open(F"./data/tx_{txid}.json", "a") as f:
        f.write(json.dumps(data))

    with open("./data/transfer_hex_list.log", "a") as f:
        f.write(data["txid"] + "\n")


def load_transfer_hex_list():
    # 按行读取文件，返回列表
    with open("./data/transfer_hex_list.log", "r") as f:
        return f.read().splitlines()


def load_transfer_hex(txid):
    # 读取json文件，解析为字典
    with open(F"./data/tx_{txid}.json", "r") as f:
        return json.loads(f.read())


def log_statistics(replenished_data, c):
    revenue = 0
    user = 0
    request_num = 0
    for k, v in replenished_data.items():
        if k.startswith("f"):
            user += 1
            request_num += 1
        else:
            revenue += v
    with open(F"./data/statistics.log", "a") as f:
        f.write(F'{today()}|{user}|{revenue}|{request_num}|1|{c}\n')


def get_statistics():
    data = {}
    with open(F"./data/statistics.log", "r") as f:
        for line in f.readlines():
            items = line.split("|")
            c = float(items[-1])
            if c < 0.02:
                c_type = 1
            elif c < 0.1:
                c_type = 2
            elif c < 0.3:
                c_type = 3
            else:
                c_type = 4
            if items[0] not in data:
                data[items[0]] = {
                    "user_num": int(items[1]),
                    "revenue_amount": float(items[2]),
                    "request_num": int(items[3]),
                    "transaction_num": int(items[4]),
                    "c_range1": 0,
                    "c_range2": 0,
                    "c_range3": 0,
                    "c_range4": 0,
                }
            else:
                data[items[0]]["user_num"] += int(items[1])
                data[items[0]]["revenue_amount"] += float(items[2])
                data[items[0]]["request_num"] += int(items[3])
                data[items[0]]["transaction_num"] += int(items[4])
            data[items[0]][F"c_range{c_type}"] += 1
    return data
