import math
import random

arr = [40, 20, 27, 7, 7, 33, 33]
c = 1 / 3


def replenish(arr, c):
    max_value = max(arr)
    sum_value = sum(arr)
    if max_value / sum_value >= c:
        replenish_sum = int(max_value / c - sum_value) + 1
        replenish_num = int(replenish_sum / max_value)
        arr += [max_value] * replenish_num
        if max_value * replenish_num < replenish_sum:
            arr.append(replenish_sum - max_value * replenish_num)
            replenish_num += 1
        return arr, replenish_num
    return arr, 0


arr, replenish_num = replenish(arr, c)


def main_dr(arr, c):
    index = list(range(len(arr)))
    arr, index = zip(*sorted(zip(arr, index), reverse=True))
    out = [[] for _ in range(len(arr))]
    max_value = arr[0]
    x = 10 ** int(math.log10(max_value))
    c_list = []
    while x >= 1:
        d = []
        r = []
        for item in arr:
            if x > 1:
                d0 = item // x
                d0 = random.randint(0, d0)
                d.append(d0)
                r.append(item - d0 * x)
            else:
                d = arr
                r = [0] * len(arr)
        if max(d) <= c * sum(d) and max(r) <= c * sum(r):
            c_list.append(max(d) / sum(d))
            for i in range(len(arr)):
                if d[i] > 0:
                    out[i].append((x, d[i]))
            arr = r
        x = x // 10
    print(out)
    out, _ = zip(*sorted(zip(out, index), key=lambda y: y[1]))
    return out, max(c_list)


print(main_dr(arr, c))


def run(arr, c):
    arr, replenish_num = replenish(arr, c)
    out, c = main_dr(arr, c)
    return arr, replenish_num, out, c
