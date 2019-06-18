# encoding: UTF-8


import numpy as np
import talib
import copy
from datetime import timedelta
import math

from vnpy.trader.vtObject import VtBarData
# 规定周期
from vnpy.trader.vtConstant import *

########################################################################
class BarGenerator(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30	）
    """

    #----------------------------------------------------------------------
    def __init__(self,
                 onBar,
                 onBar_min01,
                 onBar_min05,
                 onBar_min15,
                 onBar_min30,
                 onBar_min60,
                 onBar_day01,
                 xmin=0,
                 onXminBar=None):
        """Constructor"""
        self.bar = None             # 1分钟K线对象
        self.onBar = onBar          # 1分钟K线回调函数
        
        self.xminBar = None         # X分钟K线对象
        self.xmin = xmin            # X的值
        self.onXminBar = onXminBar  # X分钟K线的回调函数
        
        self.lastTick = None        # 上一TICK缓存对象

        self.xminBar_05 = None      # 05分钟K线对象
        self.xminBar_15 = None      # 15分钟K线对象
        self.xminBar_30 = None      # 30分钟K线对象
        self.xminBar_60 = None      # 60分钟K线对象
        self.xdayBar_01 = None      # 01日线K线对象
        self.onBarmin_01 = onBar_min01
        self.onBarmin_05 = onBar_min05
        self.onBarmin_15 = onBar_min15
        self.onBarmin_30 = onBar_min30
        self.onBarmin_60 = onBar_min60
        self.onBarday_01 = onBar_day01

    # ----------------------------------------------------------------------
    def updateTick(self, tick):
        """TICK更新"""
        newMinute = False   # 默认不是新的一分钟
        
        # 尚未创建对象
        if not self.bar:
            self.bar = VtBarData()
            self.bar.interval = INTERVAL_1M
            newMinute = True
        # 新的一分钟
        elif self.bar.datetime.minute != tick.datetime.minute:
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
            
            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)
            self.updateBar_01(self.bar)
            
            # 创建新的K线对象
            self.bar = VtBarData()
            self.bar.interval = INTERVAL_1M
            newMinute = True
            
        # 初始化新一分钟的K线数据
        if newMinute:
            self.bar.vtSymbol = tick.vtSymbol
            self.bar.symbol = tick.symbol
            self.bar.exchange = tick.exchange

            self.bar.open = tick.lastPrice
            self.bar.high = tick.lastPrice
            self.bar.low = tick.lastPrice

            # 生成一分钟K线的时间戳
            self.bar.datetime = tick.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y-%m-%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
        # 累加更新老一分钟的K线数据
        else:                                   
            self.bar.high = max(self.bar.high, tick.lastPrice)
            self.bar.low = min(self.bar.low, tick.lastPrice)

        # 通用更新部分
        self.bar.close = tick.lastPrice        
        # self.bar.datetime = tick.datetime
        self.bar.openInterest = tick.openInterest
   
        if self.lastTick:
            volumeChange = tick.volume - self.lastTick.volume   # 当前K线内的成交量
            self.bar.volume += max(volumeChange, 0)             # 避免夜盘开盘lastTick.volume为昨日收盘数据，导致成交量变化为负的情况
            
        # 缓存Tick
        self.lastTick = tick

    # ----------------------------------------------------------------------
    def updateBar(self, bar):
        """1分钟K线更新"""
        # 尚未创建对象
        if not self.xminBar:
            self.xminBar = VtBarData()
            
            self.xminBar.vtSymbol = bar.vtSymbol
            self.xminBar.symbol = bar.symbol
            self.xminBar.exchange = bar.exchange
        
            self.xminBar.open = bar.open
            self.xminBar.high = bar.high
            self.xminBar.low = bar.low            
            
            self.xminBar.datetime = bar.datetime    # 以第一根分钟K线的开始时间戳作为X分钟线的时间戳
        # 累加老K线
        else:
            self.xminBar.high = max(self.xminBar.high, bar.high)
            self.xminBar.low = min(self.xminBar.low, bar.low)
    
        # 通用部分
        self.xminBar.close = bar.close        
        self.xminBar.openInterest = bar.openInterest
        self.xminBar.volume += int(bar.volume)                
            
        # X分钟已经走完
        if not (bar.datetime.minute + 1) % self.xmin:   # 可以用X整除
            # 生成上一X分钟K线的时间戳
            self.xminBar.datetime = self.xminBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
            self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S.%f')
            
            # 推送
            self.onXminBar(self.xminBar)
            
            # 清空老K线缓存对象
            self.xminBar = None

    # ----------------------------------------------------------------------
    def generate(self):
        """手动强制立即完成K线合成"""
        self.onBar(self.bar)
        self.bar = None

    # ----------------------------------------------------------------------
    def updateBar_01(self, bar):
        # 这里是回测的数据接口
        # 收到由数据库推送过来的一分钟K线，在内部自己合成多周期K线
        self.onBarmin_01(bar)
        self.updateBar_05(bar)
        self.updateBar_15(bar)
        self.updateBar_30(bar)
        self.updateBar_60(bar)
        self.updateBarDay_01(bar)

    # ----------------------------------------------------------------------
    def updateBar_05(self, bar):
        """5分钟K线更新"""
        # 尚未创建对象
        xmin = 5

        # 当前存在K线
        if self.xminBar_05:
            # 这里是防止数据不连续，理论延迟一分钟推送大周期数据，基于所做品种都是连续性比较好的，故实盘不需考虑
            if bar.datetime >= self.xminBar_05.datetime_end:  # 可以用X整除
                bar_05 = copy.deepcopy(self.xminBar_05)
                # 清空老K线缓存对象
                self.xminBar_05 = None
                self.onBarmin_05(bar_05)

        # 如果当前没有05分钟K线，创建05分钟K线
        if not self.xminBar_05:
            self.xminBar_05 = VtBarData()
            self.xminBar_05.interval = INTERVAL_5M
            self.xminBar_05.vtSymbol = bar.vtSymbol
            self.xminBar_05.symbol = bar.symbol
            self.xminBar_05.exchange = bar.exchange

            self.xminBar_05.open = bar.open
            self.xminBar_05.high = bar.high
            self.xminBar_05.low = bar.low

            self.xminBar_05.datetime = bar.datetime
            self.xminBar_05.tradedate = bar.tradedate
            self.xminBar_05.time = bar.time

            timestart, timeend, tradeday = timeStartEnd(bar.datetime, INTERVAL_5M)
            self.xminBar_05.datetime_start = timestart
            self.xminBar_05.datetime_end = timeend

        else:
            # 累加老K线
            self.xminBar_05.high = max(self.xminBar_05.high, bar.high)
            self.xminBar_05.low = min(self.xminBar_05.low, bar.low)

        # 通用部分
        self.xminBar_05.close = bar.close
        self.xminBar_05.openInterest = bar.openInterest
        self.xminBar_05.volume += int(bar.volume)

        # X分钟已经走完
        if (bar.datetime + timedelta(minutes=1)) >= self.xminBar_05.datetime_end:
            # 推送，这里不管几分钟的K线回调函数都是一个，再由K线回调函数进行广播
            bar_05 =copy.deepcopy(self.xminBar_05)
            # 清空老K线缓存对象
            self.xminBar_05 = None
            self.onBarmin_05(bar_05)

    # ----------------------------------------------------------------------
    def updateBar_15(self, bar):
        """15分钟K线更新"""
        # 尚未创建对象
        xmin = 15
        # 当前存在K线
        if self.xminBar_15:
            # 这里是防止数据不连续，理论延迟一分钟推送大周期数据，基于所做品种都是连续性比较好的，故实盘不需考虑
            if bar.datetime >= self.xminBar_15.datetime_end:  # 可以用X整除
                bar_15 = copy.deepcopy(self.xminBar_15)
                # 清空老K线缓存对象
                self.xminBar_15 = None
                self.onBarmin_15(bar_15)


        if not self.xminBar_15:
            self.xminBar_15 = VtBarData()
            self.xminBar_15.interval = INTERVAL_15M

            self.xminBar_15.vtSymbol = bar.vtSymbol
            self.xminBar_15.symbol = bar.symbol
            self.xminBar_15.exchange = bar.exchange

            self.xminBar_15.open = bar.open
            self.xminBar_15.high = bar.high
            self.xminBar_15.low = bar.low

            self.xminBar_15.datetime = bar.datetime

            self.xminBar_15.tradedate = bar.tradedate
            self.xminBar_15.time = bar.time

            timestart, timeend, tradeday = timeStartEnd(bar.datetime, INTERVAL_15M)
            self.xminBar_15.datetime_start = timestart
            self.xminBar_15.datetime_end = timeend

        # 累加老K线
        else:
            self.xminBar_15.high = max(self.xminBar_15.high, bar.high)
            self.xminBar_15.low = min(self.xminBar_15.low, bar.low)

        # 通用部分
        self.xminBar_15.close = bar.close
        self.xminBar_15.openInterest = bar.openInterest
        self.xminBar_15.volume += int(bar.volume)

        # X分钟已经走完
        if (bar.datetime + timedelta(minutes=1)) >= self.xminBar_15.datetime_end:
        # if not (bar.datetime.minute + 1) % xmin:  # 可以用X整除

            # 推送，这里不管几分钟的K线回调函数都是一个，再由K线回调函数进行广播
            bar_15 = copy.deepcopy(self.xminBar_15)
            # 清空老K线缓存对象
            self.xminBar_15 = None
            self.onBarmin_15(bar_15)


    # ----------------------------------------------------------------------
    def updateBar_30(self, bar):
        """30分钟K线更新"""
        # 尚未创建对象
        xmin = 30

        # 当前存在K线
        if self.xminBar_30:
            # 这里是防止数据不连续，理论延迟一分钟推送大周期数据，基于所做品种都是连续性比较好的，故实盘不需考虑
            if bar.datetime >= self.xminBar_30.datetime_end:
                bar_30 = copy.deepcopy(self.xminBar_30)
                # 清空老K线缓存对象
                self.xminBar_30 = None
                self.onBarmin_30(bar_30)

        if not self.xminBar_30:
            self.xminBar_30 = VtBarData()
            self.xminBar_30.interval = INTERVAL_30M

            self.xminBar_30.vtSymbol = bar.vtSymbol
            self.xminBar_30.symbol = bar.symbol
            self.xminBar_30.exchange = bar.exchange

            self.xminBar_30.open = bar.open
            self.xminBar_30.high = bar.high
            self.xminBar_30.low = bar.low

            self.xminBar_30.datetime = bar.datetime  # 以第一根分钟K线的开始时间戳作为X分钟线的时间戳

            self.xminBar_30.tradedate = bar.tradedate
            self.xminBar_30.time = bar.time

            timestart, timeend, tradeday = timeStartEnd(bar.datetime, INTERVAL_30M)
            self.xminBar_30.datetime_start = timestart
            self.xminBar_30.datetime_end = timeend

        # 累加老K线
        else:
            self.xminBar_30.high = max(self.xminBar_30.high, bar.high)
            self.xminBar_30.low = min(self.xminBar_30.low, bar.low)

        # 通用部分
        self.xminBar_30.close = bar.close
        self.xminBar_30.openInterest = bar.openInterest
        self.xminBar_30.volume += int(bar.volume)

        # X分钟已经走完
        if (bar.datetime + timedelta(minutes=1)) >= self.xminBar_30.datetime_end:
        # if not (bar.datetime.minute + 1) % xminL:
            # 推送，这里不管几分钟的K线回调函数都是一个，再由K线回调函数进行广播
            bar_30 = copy.deepcopy(self.xminBar_30)
            # 清空老K线缓存对象
            self.xminBar_30 = None
            self.onBarmin_30(bar_30)

    # ----------------------------------------------------------------------
    def updateBar_60(self, bar):
        """60分钟 1小时K线更新"""
        # 尚未创建对象
        xmin = 60

        # 当前存在K线
        if self.xminBar_60:
            # 这里是防止数据不连续，理论延迟一分钟推送大周期数据，基于所做品种都是连续性比较好的，故实盘不需考虑
            if bar.datetime >= self.xminBar_60.datetime_end:  # 可以用X整除
                bar_60 = copy.deepcopy(self.xminBar_60)
                # 清空老K线缓存对象
                self.xminBar_60 = None
                self.onBarmin_60(bar_60)

        if not self.xminBar_60:
            self.xminBar_60 = VtBarData()
            self.xminBar_60.interval = INTERVAL_60M

            self.xminBar_60.vtSymbol = bar.vtSymbol
            self.xminBar_60.symbol = bar.symbol
            self.xminBar_60.exchange = bar.exchange

            self.xminBar_60.open = bar.open
            self.xminBar_60.high = bar.high
            self.xminBar_60.low = bar.low

            self.xminBar_60.datetime = bar.datetime  # 以第一根分钟K线的开始时间戳作为X分钟线的时间戳

            self.xminBar_60.tradedate = bar.tradedate
            self.xminBar_60.time = bar.time

            timestart, timeend, tradeday = timeStartEnd(bar.datetime, INTERVAL_60M)
            self.xminBar_60.datetime_start = timestart
            self.xminBar_60.datetime_end = timeend

        # 累加老K线
        else:
            self.xminBar_60.high = max(self.xminBar_60.high, bar.high)
            self.xminBar_60.low = min(self.xminBar_60.low, bar.low)

        # 通用部分
        self.xminBar_60.close = bar.close
        self.xminBar_60.openInterest = bar.openInterest
        self.xminBar_60.volume += int(bar.volume)

        # 60分钟已经走完，60分钟走完的逻辑需要两个，一个是59分钟的时候，和其它一样
        # 另外一个是新K线的datetime不等于老K线的datetime，也就是当一分钟线不连续的时候
        if (bar.datetime + timedelta(minutes=1)) >= self.xminBar_60.datetime_end:
        # if (bar.datetime.hour != self.xminBar_60.datetime.hour) or (not (bar.datetime.minute + 1) % xmin):  # 可以用X整除

            # 推送，这里不管几分钟的K线回调函数都是一个，再由K线回调函数进行广播
            bar_60 = copy.deepcopy(self.xminBar_60)
            # 清空老K线缓存对象
            self.xminBar_60 = None
            self.onBarmin_60(bar_60)

    # ----------------------------------------------------------------------
    def updateBarDay_01(self, bar):
        """日K线更新"""

        # 当前存在K线
        if self.xdayBar_01:
            # 这里是防止数据不连续，理论延迟一分钟推送大周期数据，基于所做品种都是连续性比较好的，故实盘不需考虑
            if bar.datetime >= self.xdayBar_01.datetime_end:  # 可以用X整除
                bar_01 = copy.deepcopy(self.xdayBar_01)
                # 清空老K线缓存对象
                self.xdayBar_01 = None
                self.onBarday_01(bar_01)

        # 尚未创建对象
        if not self.xdayBar_01:
            self.xdayBar_01 = VtBarData()
            self.xdayBar_01.interval = INTERVAL_1D

            self.xdayBar_01.vtSymbol = bar.vtSymbol
            self.xdayBar_01.symbol = bar.symbol
            self.xdayBar_01.exchange = bar.exchange

            self.xdayBar_01.open = bar.open
            self.xdayBar_01.high = bar.high
            self.xdayBar_01.low = bar.low

            self.xdayBar_01.datetime = bar.datetime

            self.xdayBar_01.tradedate = bar.tradedate
            self.xdayBar_01.time = bar.time

            timestart, timeend, tradeday = timeStartEnd(bar.datetime, INTERVAL_1D)
            self.xdayBar_01.datetime_start = timestart
            self.xdayBar_01.datetime_end = timeend

        # 累加老K线
        else:
            self.xdayBar_01.high = max(self.xdayBar_01.high, bar.high)
            self.xdayBar_01.low = min(self.xdayBar_01.low, bar.low)

        # 通用部分
        self.xdayBar_01.close = bar.close
        self.xdayBar_01.openInterest = bar.openInterest
        self.xdayBar_01.volume += int(bar.volume)

        # 一天的K线已经走完
        # 这里添加日线的走完的逻辑，不同的逻辑不一样
        if (bar.datetime + timedelta(minutes=1)) >= self.xdayBar_01.datetime_end:
        #if bar.tradedate != self.xdayBar_01.tradedate:
            bar_day_01 = copy.deepcopy(self.xdayBar_01)
            # 清空老K线缓存对象
            self.xdayBar_01 = None
            self.onBarday_01(bar_day_01)

    # ----------------------------------------------------------------------
    def generate_05(self):
        """
        手动强制立即合成05分钟K线
        """
        bar_05 = copy.deepcopy(self.xminBar_05)
        # 清空老K线缓存对象
        self.xminBar_05 = None
        self.onBar(bar_05)

    # ----------------------------------------------------------------------
    def generate_15(self):
        """强制合成15分钟K线"""
        bar_15 = copy.deepcopy(self.xminBar_15)
        # 清空老K线缓存对象
        self.xminBar_15 = None
        self.onBar(bar_15)


    # ----------------------------------------------------------------------
    def generate_30(self):
        """强制合成30分钟K线"""
        bar_30 = copy.deepcopy(self.xminBar_30)
        # 清空老K线缓存对象
        self.xminBar_30 = None
        self.onBar(bar_30)

    # ----------------------------------------------------------------------
    def generate_60(self):
        """强制合成60分钟K线"""
        bar_60 = copy.deepcopy(self.xminBar_60)
        # 清空老K线缓存对象
        self.xminBar_60 = None
        self.onBar(bar_60)

    # ----------------------------------------------------------------------
    def generate_day_01(self):
        """强制合成01日K线"""
        bar_day_01 = copy.deepcopy(self.xdayBar_01)
        # 清空老K线缓存对象
        self.xdayBar_01 = None
        self.onBar(bar_day_01)

    # ----------------------------------------------------------------------
    def generate_timeRange(self, datetime, period, min):
        # 输入datetime对象,周期,和数（比如5,15,30等），获得起始时间和结束时间

        pass



########################################################################
class ArrayManager(object):
    """
    K线序列管理工具，负责：
    1. K线时间序列的维护
    2. 常用技术指标的计算
    """

    #----------------------------------------------------------------------
    def __init__(self, size=10000000):
        """Constructor"""
        self.count = 0                      # 缓存计数
        self.size = size                    # 缓存大小
        self.inited = False                 # True if count>=size

        self.timeArray = []
        self.openArray = []
        self.highArray = []
        self.lowArray = []
        self.closeArray = []
        self.volumeArray = []
        """
        self.openArray = np.zeros(size)     # OHLC
        self.highArray = np.zeros(size)
        self.lowArray = np.zeros(size)
        self.closeArray = np.zeros(size)
        self.volumeArray = np.zeros(size)
        """
        
    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """更新K线"""
        self.count += 1
        #if not self.inited and self.count >= self.size:
        if not self.inited and self.count >= 100:
            self.inited = True

        # self.timeArray[:-1] = self.timeArray[1:]
        # self.openArray[:-1] = self.openArray[1:]
        # self.highArray[:-1] = self.highArray[1:]
        # self.lowArray[:-1] = self.lowArray[1:]
        # self.closeArray[:-1] = self.closeArray[1:]
        # self.volumeArray[:-1] = self.volumeArray[1:]

        self.timeArray.append(bar.datetime.strftime("%Y-%m-%d %H:%M:%S"))
        self.openArray.append(bar.open)
        self.highArray.append(bar.high)
        self.lowArray.append(bar.low)
        self.closeArray.append(bar.close)
        self.volumeArray.append(bar.volume)
        """
        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low        
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume
        """
    # ----------------------------------------------------------------------
    @property
    def time(self):
        """获取时间序列"""
        return self.timeArray

    #----------------------------------------------------------------------
    @property
    def open(self):
        """获取开盘价序列"""
        return self.openArray
        
    #----------------------------------------------------------------------
    @property
    def high(self):
        """获取最高价序列"""
        return self.highArray
    
    #----------------------------------------------------------------------
    @property
    def low(self):
        """获取最低价序列"""
        return self.lowArray
    
    #----------------------------------------------------------------------
    @property
    def close(self):
        """获取收盘价序列"""
        return self.closeArray
    
    #----------------------------------------------------------------------
    @property    
    def volume(self):
        """获取成交量序列"""
        return self.volumeArray
    
    #----------------------------------------------------------------------
    def sma(self, n, array=False):
        """简单均线"""
        result = talib.SMA(np.array(self.close), n)
        if array:
            return result
        return result[-1]

    #----------------------------------------------------------------------
    def ema(self, n, array=False):
        """指数平均数指标"""
        result = talib.EMA(np.array(self.close), n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def std(self, n, array=False):
        """标准差"""
        result = talib.STDDEV(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def cci(self, n, array=False):
        """CCI指标"""
        result = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def atr(self, n, array=False):
        """ATR指标"""
        result = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def rsi(self, n, array=False):
        """RSI指标"""
        result = talib.RSI(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def macd(self, fastPeriod, slowPeriod, signalPeriod, array=False):
        """MACD指标"""
        macd, signal, hist = talib.MACD(self.close, fastPeriod,
                                        slowPeriod, signalPeriod)
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]
    
    #----------------------------------------------------------------------
    def adx(self, n, array=False):
        """ADX指标"""
        result = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def boll(self, n, dev, array=False):
        """布林通道"""
        mid = self.sma(n, array)
        std = self.std(n, array)
        
        up = mid + std * dev
        down = mid - std * dev
        
        return up, down    
    
    #----------------------------------------------------------------------
    def keltner(self, n, dev, array=False):
        """肯特纳通道"""
        mid = self.sma(n, array)
        atr = self.atr(n, array)
        
        up = mid + atr * dev
        down = mid - atr * dev
        
        return up, down
    
    #----------------------------------------------------------------------
    def donchian(self, n, array=False):
        """唐奇安通道"""
        up = talib.MAX(self.high, n)
        down = talib.MIN(self.low, n)
        
        if array:
            return up, down
        return up[-1], down[-1]




# 数字货币时间处理，处理本地时间与ISO时间
def timeStartEnd(time, interval):

    # 这里暂时先简化处理，按正常时间处理即可
    # 先处理tradeday交易日期的问题
    tradeday = time.strftime("%Y-%m-%d")

    if interval == INTERVAL_5M:
        minstart = math.floor(time.minute / 5) * 5
        timestart = time.replace(minute=minstart)
        timeend = timestart + timedelta(minutes=5, seconds=0)
        return timestart, timeend, tradeday
    elif interval == INTERVAL_15M:
        minstart = math.floor(time.minute / 15) * 15
        timestart = time.replace(minute=minstart)
        timeend = timestart + timedelta(minutes=15, seconds=0)
        return timestart, timeend, tradeday
    elif interval == INTERVAL_30M:
        minstart = math.floor(time.minute / 30) * 30
        timestart = time.replace(minute=minstart)
        timeend = timestart + timedelta(minutes=30, seconds=0)
        return timestart, timeend, tradeday
        # 60分钟这里
    elif interval == INTERVAL_60M:
        timestart = time.replace(minute=0)
        timeend = timestart + timedelta(hours=1)
        return timestart, timeend, tradeday
    elif interval == INTERVAL_1D:
        # 日线这里
        timestart = time.replace(hour=0)
        timeend = timestart + timedelta(days=1)
        return timestart, timeend, tradeday
    else:
        timestart = None
        timeend = None

        print('输入的时间周期有误，请重新输入')


    return timestart, timeend, tradeday
