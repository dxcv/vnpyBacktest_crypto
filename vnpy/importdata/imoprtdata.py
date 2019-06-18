#!/usr/bin/env python
# encoding: UTF-8


from vnpy.trader.app.ctaStrategy.ctaHistoryData import loadTbCsv

def example1():
    fileName = "D:\\PycharmProjects\\vnpy_backetst\\test.csv"
    dbName = 'VnTrader_1Min_Db'
    symbol = "rb"
    loadTbCsv(fileName, dbName, symbol)


if __name__ == "__main__":
    example1()