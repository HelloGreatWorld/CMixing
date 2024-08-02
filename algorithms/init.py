import json

from utils import get_data, load_addresses, floor, confirm


def init():
    # 钱包的概念等于用户
    # 初始化链上数据
    # 创建矿工钱包（miner）及矿工收款地址 *1
    # 创建from钱包（f1-f10）及input地址 *1/f
    # 创建Coordinator钱包（c）及Coordinator地址 *100及找零地址 *1
    # 创建to钱包（t1-t10）to地址 *100
    data = {}

    # 创建矿工账户
    get_data("createwallet", {"wallet_name": "miner", "load_on_startup": True})
    data["miner"] = {}
    # 创建矿工收款地址
    _, d = get_data("getnewaddress", {"label": "miner.m"}, wallet="miner")
    data["miner"] = {
        "m": d
    }
    # 创建from账户
    data["f"] = {}
    for i in range(1, 11):
        get_data("createwallet", {"wallet_name": f"f{i}", "load_on_startup": True})
        _, d = get_data("getnewaddress", {"label": f"f{i}"}, wallet=f"f{i}")
        data["f"][f"f{i}"] = d
    # 创建Coordinator账户
    data["c"] = {}
    get_data("createwallet", {"wallet_name": "c", "load_on_startup": True})
    # 创建Coordinator地址
    data["c"] = {}
    data["c"]["c"] = []
    for i in range(1, 101):
        _, d = get_data("getnewaddress", {"label": f"c"}, wallet="c")
        data["c"]["c"].append(d)
    _, d = get_data("getnewaddress", {"label": f"change"}, wallet="c")
    data["c"]["change"] = d
    # 创建to账户
    data["t"] = {}
    for i in range(1, 11):
        get_data("createwallet", {"wallet_name": f"t{i}", "load_on_startup": True})
        data["t"][f"t{i}"] = []
        for j in range(1, 101):
            _, d = get_data("getnewaddress", {"label": f"t{i}"}, wallet=f"t{i}")
            data["t"][f"t{i}"].append(d)
    # 将data以json格式保存到文件
    with open("./data/addresses.json", "w") as f:
        f.write(json.dumps(data))
    print("finish")


# 判断是否存在addresses.json文件
try:
    with open("./data/addresses.json", "r") as f:
        pass
except FileNotFoundError:
    init()

addresses = load_addresses()

# 生成200个区块，用于获取初始币
#get_data("generatetoaddress", [200, addresses["miner"]["m"]], wallet="miner")

# 展示miner中余额
print(get_data("getbalance", wallet="miner"))

# 将miner中的币平均转移的f和c当中

ads = [addresses["c"]["change"]]
for i in range(1, 11):
    ads.append(addresses["f"][f"f{i}"])

get_data("sendall", {"recipients": ads}, wallet="miner")
confirm(addresses["miner"]["m"])
