
import math
import numpy as np
import os
import sys
import csv
import datetime
import pandas as pd
from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
from vnpy.app.cta_strategy.base import BacktestingMode
from vnpy.app.cta_strategy import (
    CtaTemplate,
    TickData,
    TradeData,
    OrderData,
)

feature_cols = ['custom_feature']

"""
构建自己的tick数据，这样可以通过pandas来向量化计算feature
"""
class MLTickData(TickData):
    def __init__(self,**kargs):
        for key in feature_cols:
            setattr(self,key,kargs[key])
            del(kargs[key])
        TickData.__init__(self,**kargs)

class MLStrategy(CtaTemplate):

    def __init__(self,cta_engine,strategy_name,vt_symbol,setting):
        CtaTemplate.__init__(self,cta_engine,strategy_name,vt_symbol,setting)
        self.model = setting['model']
        self.features = feature_cols

    def on_init(self):
        print("ml strategy init")
        self.load_tick(0)

    def on_start(self):
        print("ml strategy start")

    def on_tick(self,tick:MLTickData):
        feature_datas = []
        for key in self.features:
            feature_datas += [getattr(tick,key)]
        predict = self.model.predict([feature_datas])[0]
        ret = math.exp(predict)
        print('predict',ret)
        if self.pos>0:
            if ret>1.0003:
                return
            elif ret>1 and ret<1.0002:
                self.cancel_all()
                self.sell(tick.ask_price_1,self.pos)
            elif ret<0.9997:
                self.cancel_all()
                # cover
                self.sell(tick.ask_price_1,self.pos)
                # short
                self.short(tick.ask_price_1,0.1)
        elif self.pos<0:
            if ret<0.9997:
                return
            elif ret>0.9997 and ret<0.9998:
                self.cancel_all()
                self.cover(tick.bid_price_1,abs(self.pos))
            elif ret>1.0003:
                self.cancel_all()
                self.cover(tick.bid_price_1,abs(self.pos))
                self.buy(tick.bp1,0.1)
        elif self.pos==0:
            if ret<0.9997:
                self.short(tick.ask_price_1,0.1)
            elif ret>1.0003:
                self.buy(tick.bid_price_1,0.1)
        
    def on_trade(self,trade:TradeData):
        self.put_event()

# tick转换
def mapCol(item)->object:
    """
    dataframe中的字段转换一下
    """
    colMap = {}
    for i in range(1,6):
        colMap['ask_price_{}'.format(i)] = float(item["ap{}".format(i)])
        colMap['ask_volume_{}'.format(i)] = float(item["aq{}".format(i)])
        colMap['bid_price_{}'.format(i)] = float(item["bp{}".format(i)])
        colMap['bid_volume_{}'.format(i)] = float(item["bq{}".format(i)])
    return colMap

# 将feature设置到自定义tick上
def mapFeature(item)->object:
    featureMap = {}
    for key in feature_cols:
        featureMap[key] = item[key]
    return featureMap

data = testData.apply(lambda item:MLTickData(
                symbol="BTC",
                exchange=Exchange.BINANCE,
                datetime=item.timestamp,
                **mapFeature(item),
                **mapCol(item),
),axis=1)


engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol="BTC.BINANCE",
    interval="1m",
    start=datetime(2020,5,19),
    end=datetime(2021,5,22),
    rate=0,
    slippage=0,
    size=.1,
    pricetick=5,
    capital=100000,
    mode=BacktestingMode.TICK,
    inverse=True,
)
engine.add_strategy(MLStrategy,setting={"model":model})
# engine.load_data()

# 设置历史数据
engine.history_data = data

engine.run_backtesting()

# 显示逐笔统计数据
engine.exhaust_trade_result(engine.trades)