import random

from fastapi import FastAPI, Body
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

from utils import s, return_data, mock, DECIMALS, log_process, floor, get_data, log_transfer, log_statistics, \
    get_statistics, log_transfer_data, load_transfer_hex, load_transfer_hex_list
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def logger(*message):
    print(message)


# 错误处理，主要处理用于统一格式
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=200,
        content={
            "error": exc.status_code,
            "data": exc.detail,
        },
    )


# 从文件中加载json数据
import json

with open("./data/addresses.json", "r") as f:
    address_list = json.loads(f.read())


# 获取指定钱包的余额


@app.get('/{wallet}/balance')
async def balance(wallet: str):
    """
    获取指定钱包的余额
    - :param
        - wallet:
    - :return:
        - n    (numeric) The total amount in BTC received for this wallet.

    https://bitcoincore.org/en/doc/27.0.0/rpc/wallet/getbalance/
    """
    return return_data("getbalance", wallet=wallet)


# 预转账计算
@app.post('/{wallet}/pre_transfer')
async def pre_transfer(wallet: str, amount: float = Body(embed=True), method: str = Body(embed=True),
                       c: float = Body(embed=True)):
    """
    预转账拆分计算
    - param
        - wallet:
        - amount:
        - method: dr|dg|boggart
        - c:
    - return:
        - data: 增加其他用户数据
        - replenished_data: 增加协调这数据
        - processed_data: 拆分方案
        - c: 拆分后真实c
    """
    if method == 'dr':
        from dr import run
    elif method == 'dg':
        from dg import run
    elif method == 'boggart':
        from boggart import run
    else:
        return {"error": -1, "data": "method not found"}

    # 随机生成
    data = mock(wallet, amount)
    keys = []
    arr = []
    for k, v in data.items():
        keys.append(k)
        arr.append(int(v * DECIMALS))
    arr, replenish_num, out, c0 = run(arr, c)
    c0 = floor(c0, 4)
    pd = {}
    replenished_data = {}
    for i in range(len(arr)):
        if i < len(keys):
            pd[keys[i]] = [[item[0] / DECIMALS, item[1]] for item in out[i]]
            replenished_data[keys[i]] = arr[i] / DECIMALS
        else:
            pd[f"c{i}"] = [[item[0] / DECIMALS, item[1]] for item in out[i]]
            replenished_data[f"c{i}"] = arr[i] / DECIMALS
    log_process(pd, c0)
    log_statistics(replenished_data, c0)
    return s({
        "data": data,
        "replenished_data": replenished_data,
        "processed_data": pd,
        "c": c0,
    })


def make_transfer(key, t100, charge, value, total, fee_rate=0.01, fee_address="c"):
    d = {}
    inputs = []
    outputs = {}
    o = []
    t_num = sum([item[1] for item in value])
    t_list = random.sample(t100, t_num)
    for j in value:
        for k in range(j[1]):
            amount = round(j[0], 2)
            address = t_list.pop()
            d[address] = amount
    fee = round(total * fee_rate, 8)
    if fee <= 0.00001:
        fee = 0.00001
    d[fee_address] = fee
    print("value:", value)
    print("d:", d)
    _, res = get_data("createrawtransaction", [[], d])
    _, res = get_data("fundrawtransaction", [res, {"changeAddress": charge}], wallet=key)
    change_pos = res['changepos']
    x = 0
    _, res = get_data("decoderawtransaction", [res["hex"]])
    for i in res["vin"]:
        inputs.append({"txid": i["txid"], "vout": i["vout"]})
    for i in res["vout"]:
        outputs[i["scriptPubKey"]["address"]] = i["value"]
        if fee == i["value"] and fee_address == i["scriptPubKey"]["address"]:
            print("fee:", total, fee_rate, i["value"])
            o.append({
                "flag": "c",
                "wallet": key,
                "address": i["scriptPubKey"]["address"],
                "amount": i["value"],
                "type": "fee",
            })
        else:
            o.append({
                "flag": "c" if key.startswith("c") else key[1:],
                "wallet": key,
                "address": i["scriptPubKey"]["address"],
                "amount": i["value"],
                "type": "change" if x == change_pos else "output",
            })
        x += 1
    return inputs, outputs, o


@app.get('/{wallet}/transfer/{txid}')
async def transfer_by_txid(wallet: str, txid: str):
    """
    通过txid获取交易信息
    - :param
        - wallet: 钱包名称
        - txid: 交易id
    - :return:
        - data: 交易数据 同post：/transfer
    """
    try:
        data = load_transfer_hex(txid)
    except Exception as e:
        return {"error": -1, "data": str(e)}
    return s(data)


@app.get('/{wallet}/probability/{txid}')
async def probability(wallet: str, txid: str):
    """
    通过txid获取交易概率
    - :param
        - wallet: 钱包名称
        - txid: 交易id
    - :return:
        - 每个input对应每个output的概率，第一层为input地址作为key的字典，第二层为output数组
    """
    try:
        data = load_transfer_hex(txid)
    except Exception as e:
        return {"error": -1, "data": str(e)}
    amount_dict = {}
    input_dict = {}
    for key, out in data["format_data"]["output"].items():
        amount_dict[out["value"]] = amount_dict.get(out["value"], 0) + 1
        if out["flag"] != "c":
            if input_dict.get(out["flag"]) is None:
                input_dict[out["flag"]] = {}
            input_dict[out["flag"]][out["value"]] = input_dict[out["flag"]].get(out["value"], 0) + 1
    d = {}
    for input_address, input in data["format_data"]["input"].items():
        if input["flag"] == "c":
            continue
        d[input_address] = []
        for out_address, out in data["format_data"]["output"].items():
            amount_key = out["value"]
            d[input_address].append({
                "address": out_address,
                "value": out["value"],
                "flag": out["flag"],
                "probability": floor((input_dict[input["flag"]][amount_key]) / (amount_dict[amount_key]), 4) if
                input_dict[input["flag"]].get(amount_key, 0) else 0,
            })
    return s(d)


@app.get('/{wallet}/v0/probability/{txid}')
async def probability_old(wallet: str, txid: str):
    """
    【废弃】通过txid获取交易概率
    """
    try:
        data = load_transfer_hex(txid)
    except Exception as e:
        return {"error": -1, "data": str(e)}
    total = {}
    input = {}
    vk = {}
    d = {}
    for key, input in data["format_data"]["input"].items():
        vk[input["flag"]] = key
        if input["flag"] != "c":
            d[key] = []
    for key, output in data["format_data"]["output"].items():
        total[output["value"]] = total.get(output["value"], 0) + 1
        if input.get(output["flag"]) is None:
            input[output["flag"]] = {}
        input[output["flag"]][output["value"]] = input[output["flag"]].get(output["value"], 0) + 1
    for key, value in data["format_data"]["output"].items():
        d[vk[value["flag"]]].append({
            "address": key,
            "value": value["value"],
            "probability": floor(input[value["flag"]][value["value"]] / total[value["value"]], 4),
        })
    return s(d)


@app.get('/{wallet}/transfer')
async def transfer_list(wallet: str):
    """
    获取所有交易列表
    - :param
        - wallet:
    - :return:
        - data: 交易列表
    """

    return s(load_transfer_hex_list())


@app.post('/{wallet}/transfer')
async def transfer(wallet: str, fee_rate: float = 0.01, data=Body()):
    """
    转账
    - :param
        - wallet: 钱包名称
        - data: 列表，格式于pre_transfer返回的processed_data相同
    - :return:
        - txid: 交易id
        - blockhash: 区块hash
        - block: 区块数据
        - input_num: 输入数量
        - output_num: 输出数量
        - format_data: 拆分方案
    """
    log = {
        "inputs": [],
        "outputs": [],
    }
    inputs = []
    outputs = {}
    sign_wallets = []
    has_c = False
    format_data = {
        "input": {},
        "output": {},
    }
    fee_address = address_list.get("c", {}).get("change")
    for key, value in data.items():
        d = {}
        id = key[1:]
        w = key
        amount = round(sum([item[0] * item[1] for item in value]), 2)

        if key.startswith("f"):
            sign_wallets.append(key)
            change = address_list.get("f", {}).get(key)
            log["inputs"].append({
                "flag": id,
                "wallet": key,
                "address": change,
                "amount": amount,
            })
            t100 = address_list.get("t", {}).get(F"t{id}")
            v = [] + value
        else:
            if has_c:
                continue
            has_c = True
            sign_wallets.append("c")
            w = "c"
            change = address_list.get("c", {}).get("change")

            t100 = address_list.get("c", {}).get("c")
            v = []
            for k, v0 in data.items():
                if k.startswith("c"):
                    print(v0)
                    v += v0
            log["inputs"].append({
                "flag": "c",
                "wallet": "c",
                "address": change,
                "amount": amount,
            })
        format_data_input = format_data["input"].get(change, -1)
        if format_data_input == -1:
            format_data["input"][change] = {
                "value": amount,
                "flag": "c" if key.startswith("c") else key[1:],
            }
        else:
            format_data["input"][change]["value"] += amount
        i, o, log_o = make_transfer(w, t100, change, v, amount, fee_rate, fee_address)
        for v in log_o:
            if v['type'] == 'fee' and format_data["output"].get(fee_address):
                format_data["output"][fee_address] = {
                    "value": round(format_data["output"][fee_address]["value"] + v["amount"], 4),
                    "flag": v["flag"],
                    "type": v["type"],
                }
            else:
                format_data["output"][v["address"]] = {
                    "value": v["amount"],
                    "flag": v["flag"],
                    "type": v["type"],
                }
        print("o:", o)

        log["outputs"] += log_o
        inputs += i

        if outputs.get(fee_address):
            outputs[fee_address] = round(o.pop(fee_address) + outputs[fee_address], 8)
        outputs.update(o)
    _, res = get_data("createrawtransaction", [inputs, outputs])
    for w in sign_wallets:
        if isinstance(res, str):
            hex = res
        else:
            hex = res["hex"]
        _, res = get_data("signrawtransactionwithwallet", [hex], wallet=w)
    return s(res)
    _, res = get_data("sendrawtransaction", [res["hex"]])
    _, bs = get_data('generatetoaddress', [6, address_list.get("miner", {}).get("m")], wallet="miner")
    log_transfer(res + "|" + bs[0], log)
    _, block = get_data("getblock", [bs[0], 3])
    for tx in block["tx"]:
        if tx["txid"] == res:
            out_data = {
                "format_data": format_data,
                "wallet": sign_wallets[-1],
                "txid": res,
                "blockhash": bs[0],
                "block": block,
                "fee": tx["fee"],
                "input_num": len(tx["vin"]),
                "output_num": len(tx["vout"]),
            }
            log_transfer_data(out_data)

            return s(out_data)
    return s({
        "wallet": sign_wallets[-1],
        "txid": res,
        "blockhash": bs[0],
    })


# 通过钱包名称获取名下的所有地址
# wallet t1-t10
@app.get('/{wallet}/addresses')
async def addresses(wallet: str):
    """
    通过钱包名称获取名下的所有地址
    - :param
        - wallet: 钱包名称
    - :return:
        - data: 地址列表
    """
    return s(address_list.get("t").get("t1", []))


# 确认
@app.get('/confirm')
async def confirm():
    """
    通过生成6个块，确认交易

    """
    return return_data('generatetoaddress', [6, address_list.get("miner", {}).get("m")], wallet="miner")


# 查看链上数据
@app.get('/block/{id}')
async def get_tx(id: str):
    """
    查看链上数据
    - :param
        - id: 交易id
    - :return:
        - data: 交易数据
    https://bitcoincore.org/en/doc/27.0.0/rpc/blockchain/getblock/
    """
    return return_data('getblock', [id, 3])


@app.get('/statistics')
async def statistics():
    """
    获取统计数据
    - return:
        - user_num: 用户数量
        - revenue_amount: 收入
        - request_num: 请求次数
        - transaction_num: 交易次数
        - c_range1: 0.02以下
        - c_range2: 0.1以下
        - c_range3: 0.3以下
        - c_range4: 0.3以上
    """

    return s(get_statistics())
# # 0.1 创建钱包
# @app.get('/create/{name}')
# async def create(name: str):
#     err, data = r("createwallet", {"wallet_name": name}, return_response=False)
#     if err == 0:
#         return r("getnewaddress", wallet=name)
#     if err == -4:
#         return {"error": err, "data": "钱包已存在"}
#     return {"error": err, "data": data}
#
#
# # 1 Balance
# @app.get('/{wallet}/balance')
# async def balance(wallet: str):
#     err, data = r('getbalances', wallet=wallet, return_response=False)
#     if err:
#         raise E(err, data)
#     # return s({
#     #     "trusted": data["mine"]["trusted"],
#     #     "untrusted_pending": data["mine"]["untrusted_pending"],
#     # })
#     return s({
#         "available": data["mine"]["trusted"],
#         "occupied": data["mine"]["untrusted_pending"] + data["mine"]["immature"],
#     })
#
#
# # 2.0 给矿工钱包增加余额
# @app.get('/mine')
# async def mine():
#     return r('generatetoaddress', [100, MINER_ADDRESS], wallet="miner")
#
#
# # 2.1 通过生成6个块，确认交易
# @app.get('/confirm')
# async def confirm():
#     return r('generatetoaddress', [6, MINER_ADDRESS], wallet="miner")
#
#
# # 2 add budget
# @app.post('/{wallet}/add_budget')
# async def add_budget(wallet: str, amount: float = Body(..., embed=True)):
#     err, data = r('getnewaddress', wallet=wallet, return_response=False)
#     if err:
#         raise E(err, data)
#     address = data
#     err, data = r('sendtoaddress', [address, amount], wallet="miner", return_response=False)
#     if err:
#         raise E(err, data)
#     return await confirm()
#
#
# # 2 remove budget
# @app.post('/{wallet}/remove_budget')
# async def remove_budget(wallet: str, amount: float = Body(..., embed=True)):
#     err, data = r('sendtoaddress', [MINER_ADDRESS, amount], wallet=wallet, return_response=False)
#     if err:
#         raise E(err, data)
#     return await confirm()
#
#
# # 9.1 block info
# @app.get('/block/{txid}')
# async def block(txid: str):
#     err, data = r('gettransaction', [txid], return_response=False)
#     if err:
#         raise E(err, data)
#     d = {
#         "InputList": [],
#         "OutputList": [],
#     }
#     for i in data["details"]:
#         if i["category"] == "send":
#             d["InputList"].append({
#                 "hash": i["address"],
#                 "amount": -1 * i["amount"]
#             })
#         if i["category"] == "receive":
#             d["OutputList"].append({
#                 "hash": i["address"],
#                 "amount": i["amount"]
#             })
#     return s(d)
