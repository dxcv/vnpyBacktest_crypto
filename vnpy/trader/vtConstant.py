# encoding: UTF-8

from vnpy.trader.language import constant

# 将常量定义添加到vtConstant.py的局部字典中
d = locals()
for name in dir(constant):
    if '__' not in name:
        d[name] = constant.__getattribute__(name)

INTERVAL_1M = "min_01"
INTERVAL_5M = "min_05"
INTERVAL_15M = "min_15"
INTERVAL_30M = "min_30"
INTERVAL_60M = "min_60"
INTERVAL_1D = "day_01"