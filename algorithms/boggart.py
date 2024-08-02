import math
from collections import Counter


# 一个函数，输入一个数组，判断该数组中的每一个元素是否为0或相等，如果不符合返回-1，如果符合，返回数组中相等的那个值
def check(arr):
    if len(arr) == 0:
        return -1
    for i in range(1, len(arr)):
        if arr[i] != 0 and arr[i] != arr[0]:
            return -1
    return arr[0]


def core(arr):
    arr = list(arr)
    out = [[] for _ in range(len(arr))]
    filled = []
    for i in range(1, len(arr)):
        last = check(arr)
        if last != -1:
            # out数组中按照arr的顺序填充arr的值
            for j in range(len(arr)):
                if arr[j] == 0:
                    filled.append(last)
                    continue
                out[j].append(arr[j])
            break
        target = arr[0] - arr[i]
        while target > 0:
            # 获取数组中不为0的最小值
            min_value = min([item for item in arr if item != 0])
            min_value = min(min_value, target)

            for j in range(len(arr)):
                if i == j:
                    continue
                if arr[j] == 0:
                    filled.append(min_value)
                else:
                    arr[j] -= min_value
                    out[j].append(min_value)
            target -= min_value
    # print(arr, out, filled)
    return out, filled


def run(arr, c):
    m = math.ceil(1 / c) + 1

    # 填充原始数组到m的倍数，并计算填充数量
    filled_zero = m - len(arr) % m if len(arr) % m != 0 else 0
    arr += [0] * filled_zero
    filled = []
    # 排序
    index = list(range(len(arr)))
    arr, index = zip(*sorted(zip(arr, index), reverse=True))
    out = [[] for _ in range(len(arr))]

    # 按照m分组，分别调用core
    for i in range(0, len(arr), m):
        out[i:i + m], filled_arr = core(arr[i:i + m])
        filled += filled_arr
    out = out[:len(arr) - filled_zero]
    for i in range(len(out)):
        counter = Counter(out[i])
        out[i] = [[item, count] for item, count in counter.items()]
    # 恢复原顺序
    counter = Counter(filled)
    filled = [[item, count] for item, count in counter.items()]
    out, _ = zip(*sorted(zip(out, index), key=lambda y: y[1]))
    # 返回数组，包括原始数组，填充数组
    if len(filled) == 0:
        a = list(out)
    else:
        a = list(out) + [filled]
    # 各个账户总金额
    o = []
    for i in a:
        oo = 0
        for ii in i:
            oo += ii[0] * ii[1]
        o.append(oo)
    # 计算实际c值
    data = []
    for i in a:
        for ii in i:
            data += [ii[0]] * ii[1]
    counter = Counter(data)
    min_count = min(counter.values())
    c0 = 1 / min_count
    return o, 1, a, c0


test_arr = [30, 50, 60, 97, 50, 57]
test_c = 0.3
print(run(test_arr, test_c))
