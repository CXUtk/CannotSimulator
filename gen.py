import timeit
import math
import numpy as np

x, y = 3.0, 4.0  # 测试数据
vec = np.array([3.0, 4.0])

def method_hypot():
    return math.hypot(x, y)

def method_sqrt():
    return math.sqrt(x*x + y*y)

def method_numpy():
    return np.linalg.norm(vec)

# 测试结果（100万次调用）
print("math.hypot:      ", timeit.timeit(method_hypot, number=1_000_000))
print("math.sqrt:       ", timeit.timeit(method_sqrt, number=1_000_000))
print("numpy.linalg.norm:", timeit.timeit(method_numpy, number=1_000_000))