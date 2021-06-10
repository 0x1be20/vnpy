from vnpy.trader.constant import Status,Exchange
from vnpy.app.cta_strategy import (
    CtaTemplate,
    TickData,
    TradeData,
    OrderData,
)
class MDStrategy(CtaTemplate):
    def __init__(self,cta_engine,strategy_name,vt_symbol,setting):
        CtaTemplate.__init__(self,cta_engine,strategy_name,vt_symbol,setting)
        self.lastDirection = "down"
        self.direction = "long" # 目前直接设置，测试
        self.engine = cta_engine
        self.orders = {} # 挂单
        self.covers = {} # 成交之后的cover挂单
        self.price_interval = 0.003
        self.orderCount = 3
        self.relistDiff = 0.005
        self.baseSize = 0.1 
        self.multifier = 2 
        self.stop_loss = 0.01 # 止损
        self.stop_profit = 0.003


    def on_init(self):
        # 先使用5分钟数据进行预热，获得趋势方向
        pass

    def on_start(self):
        pass

    def on_tick(self,tick:TickData):    
        # 分成1，2，4，设置网格，0.3%网格,偏离0.1%重新挂单（如果没有成交的情况下）
        # 根据过去主动成交情况，判断趋势方向，分为空头趋势，多头趋势，震荡
        mid = (tick.ask_price_1+tick.bid_price_1)/2
        if len(self.orders.values())!= self.orderCount:
            # open orders
            self.placeOrders(self.orderCount,mid)
        else:
            # 查看所有的订单状态
            holding = False
            prices = []
            for order in list(self.orders.values()):
                if order['status'] == Status.ALLTRADED:
                    holding = True
                prices.append(order['price'])
            if not holding:
                if (self.direction == "long" and (abs(max(prices)-mid)/max(prices)>self.relistDiff)) or (self.direction == "short" and (abs(min(prices)-mid)/min(prices)>self.relistDiff)):
                    self.cancel_all()
    def on_order(self,order:OrderData):
        if order.vt_orderid in self.orders:
            self.orders[order.vt_orderid]['status'] = order.status
            if order.status == Status.ALLTRADED:
                # 下单平仓单
                if self.orders[order.vt_orderid]['side'] == "long":
                    orderids = self.sell(order.price*(1+self.stop_profit),order.volume)
                    # print("place cover")
                    self.covers[order.vt_orderid] = {
                        "orderid":orderids[0],
                        "price":order.price*(1+self.stop_profit),
                        "size":order.volume,
                        "side":"sell",
                        "status":Status.SUBMITTING
                    }
                else:
                    orderids = self.cover(order.price*(1-self.stop_profit),order.volume)
                    # print("place cover")
                    self.covers[order.vt_orderid] = {
                        "orderid":orderids[0],
                        "price":order.price*(1-self.stop_profit),
                        "size":order.volume,
                        "side":"cover",
                        "status":Status.SUBMITTING
                    }
            elif order.status == Status.CANCELLED:
                self.orders.pop(order.vt_orderid)

        for co in list(self.covers.keys()):
            if self.covers[co]['orderid'] == order.vt_orderid:
                self.covers[co]['status'] = order.status
                if order.status == Status.ALLTRADED:
                    # 平仓结束了，那么需要重新挂单
                    orderPrice = self.orders[co]['price']
                    orderSize = self.orders[co]['size']

                    if self.orders[co]['side'] == "long":
                        orderids = self.buy(orderPrice,orderSize)
                        self.orders[orderids[0]] = {
                            'orderid':orderids[0],
                            'price':orderPrice,
                            'size':orderSize,
                            'side':'long',
                            'status':Status.SUBMITTING
                        }
                    else:
                        orderids = self.sell(orderPrice,orderSize)
                        self.orders[orderids[0]] = {
                            'orderid':orderids[0],
                            'price':orderPrice,
                            'size':orderSize,
                            'side':'short',
                            'status':Status.SUBMITTING
                        }
                    self.orders.pop(co)
                    self.covers.pop(co)
                elif order.status == Status.CANCELLED:
                    self.covers.pop(co)

    def on_trade(self,trade:TradeData):
        pass

    def placeOrders(self,orderCount,price):
        priceDirection = -1 if  self.direction=="short" else 1
        for i in range(1,orderCount+1):
            orderPrice = price*(1-i*priceDirection*self.price_interval)
            orderSize = self.baseSize*(self.multifier**i)
            if priceDirection == 1:
                orderids = self.buy(orderPrice,orderSize)
                if len(orderids)>0:
                    self.orders[orderids[0]] = {
                        "orderid":orderids[0],
                        "price":orderPrice,
                        "side":"long",
                        "size":orderSize,
                        "status":Status.SUBMITTING
                    }
                else:
                    print("failed order")
            else:
                orderids = self.short(orderPrice,orderSize)
                if len(orderids)>0:
                    self.orders[orderids[0]] = {
                        "orderid":orderids[0],
                        "price":orderPrice,
                        "side":"short",
                        "size":orderSize,
                        "status":Status.SUBMITTING
                    }
                else:
                    print("failed order")

import pickle
with open("/Users/ww/mm/BTCUSDT_2021_5_19/0/data.pkl","rb") as f:
    orderbook = pickle.load(f)

# tick转换
def mapCol(item)->object:
    colMap = {}
    for i in range(1,6):
        colMap['ask_price_{}'.format(i)] = float(item["ap{}".format(i)])
        colMap['ask_volume_{}'.format(i)] = float(item["aq{}".format(i)])
        colMap['bid_price_{}'.format(i)] = float(item["bp{}".format(i)])
        colMap['bid_volume_{}'.format(i)] = float(item["bq{}".format(i)])
    colMap['last_price'] = float(item['ap1']+item['bp1'])/2
    return colMap
# def mapFeature(item)->object:
#     featureMap = {}
#     for key in feature_cols:
#         featureMap[key] = item[key]
#     return featureMap
data = orderbook.apply(lambda item:TickData(
                symbol="BTC",
                datetime=item.timestamp,
                exchange=Exchange.BINANCE,
                # **mapFeature(item),
                **mapCol(item),
                gateway_name="DB",       
),axis=1)


from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.gateway.okex import OkexGateway
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.cta_backtester import CtaBacktesterApp
from vnpy.app.data_manager import DataManagerApp
from vnpy.app.data_recorder import DataRecorderApp
from vnpy.trader.constant import Exchange
from vnpy.trader.object import TickData
from vnpy.trader.database import database_manager
import numpy as np
import os
import sys
import csv
import datetime
import pandas as pd
from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
from vnpy.app.cta_strategy.base import BacktestingMode
from vnpy.app.cta_strategy.strategies.atr_rsi_strategy import AtrRsiStrategy
import matplotlib.pyplot as plt
from datetime import datetime

engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol="BTC.BINANCE",
    interval="1m",
    start=datetime(2020,5,19),
    end=datetime(2021,5,22),
    rate=0,
    size=1,
    slippage=5,
    pricetick=0.1,
    capital=100000,
    mode=BacktestingMode.TICK,
    inverse=False,
)
engine.add_strategy(MDStrategy,{})
# engine.load_data()
engine.history_data = data
engine.run_backtesting()
engine.exhaust_trade_result(engine.trades)

