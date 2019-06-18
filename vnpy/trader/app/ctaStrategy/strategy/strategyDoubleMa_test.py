# encoding: UTF-8

"""
这里的Demo是一个最简单的双均线策略实现
"""

import time
import copy

from vnpy.trader.vtConstant import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarGenerator,
                                                     ArrayManager)


########################################################################
class DoubleMaStrategy(CtaTemplate):
    """双指数均线策略Demo"""
    className = 'DoubleMaStrategy'
    author = u'用Python的交易员'
    
    # 策略参数
    fastWindow = 10     # 快速均线参数
    slowWindow = 40     # 慢速均线参数
    initDays = 10       # 初始化数据所用的天数
    
    # 策略变量
    fastMa0 = EMPTY_FLOAT   # 当前最新的快速EMA
    fastMa1 = EMPTY_FLOAT   # 上一根的快速EMA
    
    slowMa0 = EMPTY_FLOAT
    slowMa1 = EMPTY_FLOAT
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastWindow',
                 'slowWindow']    
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'slowMa1']  
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DoubleMaStrategy, self).__init__(ctaEngine, setting)
        
        self.bg = BarGenerator(self.onBar,
                               self.onBar_min01,
                               self.onBar_min05,
                               self.onBar_min15,
                               self.onBar_min30,
                               self.onBar_min60,
                               self.onBar_day01,)
        self.am_min01 = copy.copy(ArrayManager())
        self.am_min05 = copy.copy(ArrayManager())
        self.am_min15 = copy.copy(ArrayManager())
        self.am_min30 = copy.copy(ArrayManager())
        self.am_min60 = copy.copy(ArrayManager())
        self.am_day01 = copy.copy(ArrayManager())
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）
        
    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()
    
    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()
        
    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)
        
    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 只有一分钟线，加入到K线合成器中
        #if bar.interval == INTERVAL_1M:
        if bar.interval == INTERVAL_1M:
            self.bg.updateBar_01(bar)

    # ----------------------------------------------------------------------
    def onBar_min01(self, bar):
        self.am_min01.updateBar(bar)
        if not self.am_min01.inited:
            return
        # print("收到01分钟数据：" + str(bar.datetime))

    # ----------------------------------------------------------------------
    def onBar_min05(self, bar):
        self.am_min05.updateBar(bar)
        if not self.am_min05.inited:
            return
        # print("收到05分钟数据from：" + str(bar.datetime_start) + " to "+ str(bar.datetime_end))
        # time.sleep(0.5)

    # ----------------------------------------------------------------------
    def onBar_min15(self, bar):
        self.am_min15.updateBar(bar)
        if not self.am_min15.inited:
            return

        # print("收到15分钟数据from：" + str(bar.datetime_start) + " to "+ str(bar.datetime_end))
        # time.sleep(0.5)

    # ----------------------------------------------------------------------
    def onBar_min30(self, bar):
        # print("收到30分钟数据from：" + str(bar.datetime_start) + " to " + str(bar.datetime_end))
        self.am_min30.updateBar(bar)
        if not self.am_min30.inited:
            return

        # time.sleep(0.5)

    # ----------------------------------------------------------------------
    def onBar_min60(self, bar):
        print("收到60分钟数据from：" + str(bar.datetime_start) + " low " + str(bar.datetime_end))
        self.am_min60.updateBar(bar)
        if not self.am_min60.inited:
            return
        # time.sleep(0.5)
        self.cancelAll()


        am = copy.copy(self.am_min60)

        # 计算快慢均线
        fastMa = am.sma(self.fastWindow, array=True)
        self.fastMa0 = fastMa[-1]
        self.fastMa1 = fastMa[-2]

        slowMa = am.sma(self.slowWindow, array=True)
        self.slowMa0 = slowMa[-1]
        self.slowMa1 = slowMa[-2]

        # 判断买卖
        crossOver = self.fastMa0 >= self.slowMa0 and self.fastMa1 <= self.slowMa1  # 金叉上穿
        crossBelow = self.fastMa0 <= self.slowMa0 and self.fastMa1 >= self.slowMa1  # 死叉下穿

        # 金叉和死叉的条件是互斥
        # 所有的委托均以K线收盘价委托（这里有一个实盘中无法成交的风险，考虑添加对模拟市价单类型的支持）
        if crossOver:
            # 如果金叉时手头没有持仓，则直接做多
            if self.pos == 0:
                self.buy(bar.close + 20, 1)
            # 如果有空头持仓，则先平空，再做多
            elif self.pos < 0:
                self.cover(bar.close + 10, 1)
                self.buy(bar.close + 20, 1)
        # 死叉和金叉相反
        elif crossBelow:
            if self.pos == 0:
                self.short(bar.close - 20, 1)
            elif self.pos > 0:
                self.sell(bar.close - 20, 1)
                self.short(bar.close - 20, 1)

        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onBar_day01(self, bar):
        # print("收到01日线数据from：" + str(bar.datetime_start) + " to " + str(bar.datetime_end))
        am = self.am_day01
        am.updateBar(bar)
        if not am.inited:
            return

        # time.sleep(0.5)

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass    









