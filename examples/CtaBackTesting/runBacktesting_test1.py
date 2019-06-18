#!/usr/bin/env python
# encoding: UTF-8




"""
展示数字货币如何执行策略回测。
"""

from vnpy.trader.app.ctaStrategy.ctaBacktesting_cryptospot import BacktestingEngine, MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.strategy.strategyDoubleMa_test import DoubleMaStrategy

if __name__ == '__main__':
    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期,起始日期十天
    engine.setStartDate('2012-01-03', 10)

    # 设置产品相关参数
    engine.setSlippage(0)           # 测试品种1跳
    # engine.setRate(0.3 / 10000)   # 万0.3
    engine.setRate(3/10000)         # 千分之二
    engine.setPriceTick(0.1)        # 测试最小价格变动
    engine.setSize(1)               # 设置单位大小
    engine.setCapital(5000)         # 本金

    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, "rb")

    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(DoubleMaStrategy, d)

    # 开始跑回测
    engine.runBacktesting()

    # 加入回测结果可视化
    from vnpy.trader.app.ctaStrategy.ctaBacktesting_view import vnpy_backtest_view
    vnpy_view = vnpy_backtest_view(engine)
    #vnpy_view.saveResult()
    vnpy_view.buy_sell_view()
    vnpy_view.daily_result_view()
    vnpy_view.saveResult()

    # engine.showBacktestingResult()
    # engine.showDailyResult()




















