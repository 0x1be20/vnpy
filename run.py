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
import os
import sys
import csv
import datetime
import pandas as pd
from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
from vnpy.app.cta_strategy.base import BacktestingMode
from vnpy.app.cta_strategy.strategies.atr_rsi_strategy import AtrRsiStrategy
from strategies.test import TestStrategy


class MyTickData(TickData):
    
    def __init__(self,*args,**kargs):
        self.custom_field = kargs['custom_field']
        del(kargs['custom_field'])
        TickData.__init__(self,*args,**kargs)
        

def run_load_csv(dirName):
    for file in os.listdir(dirName):
        if not file.endswith("depth.csv"):
            continue
        print("载入文件:{}".format(file))
        csv_load(dirName+"/"+file)

def csv_load(file):
    with open(file, "r") as f:
        cols = ['timestamp']
        for i in range(20):
            cols += ["ap{}".format(i+1),"aq{}".format(i+1)]
        for i in range(20):
            cols += ["bp{}".format(i+1),"bq{}".format(i+1)]
        reader = csv.DictReader(f,fieldnames=cols)

        ticks = []
        start = None
        count = 0

        for item in reader:
            # generate datetime
            date = float(item["timestamp"]) # ms
            dt = datetime.datetime.fromtimestamp(date/1000)

            tick = TickData(
                symbol="BTC",
                datetime=dt,
                exchange=Exchange.BINANCE,
                bid_price_1=float(item["bp1"]),
                bid_volume_1=float(item["bq1"]),
                ask_price_1=float(item["ap1"]),
                ask_volume_1=float(item["aq1"]), 
                ask_price_2=float(item['ap2']),
                ask_price_3=float(item['ap3']),
                ask_price_4=float(item['ap4']),
                ask_price_5=float(item['ap5']),
                bid_price_2=float(item['bp2']),
                bid_price_3=float(item['bp3']),
                bid_price_4=float(item['bp4']),
                bid_price_5=float(item['bp5']),
                ask_volume_2=float(item['aq2']),
                ask_volume_3=float(item['aq3']),
                ask_volume_4=float(item['aq4']),
                ask_volume_5=float(item['aq5']),
                bid_volume_2=float(item['bq2']),
                bid_volume_3=float(item['bq3']),
                bid_volume_4=float(item['bq4']),
                bid_volume_5=float(item['bq5']),
                gateway_name="DB",       
            )
            ticks.append(tick)
            # do some statistics
            count += 1
            if not start:
                start = tick.datetime
        end = tick.datetime
        database_manager.save_tick_data(ticks)
        print("插入数据", start, "-", end, "总数量：", count)

# run_load_csv("/Users/ww/mm/BTCUSDT_2021_5_19/0")

cols = ['timestamp']
for i in range(20):
    cols += ["ap{}".format(i+1),"aq{}".format(i+1)]
for i in range(20):
    cols += ["bp{}".format(i+1),"bq{}".format(i+1)]

data = pd.read_csv("/Users/ww/mm/BTCUSDT_2021_5_19/0/depth.csv",names=cols,date_parser=lambda x:pd.to_datetime(x,unit='ms'),parse_dates=['timestamp'])

def mapCol(item)->object:
    colMap = {}
    for i in range(1,6):
        colMap['ask_price_{}'.format(i)] = float(item["ap{}".format(i)])
        colMap['ask_volume_{}'.format(i)] = float(item["aq{}".format(i)])
        colMap['bid_price_{}'.format(i)] = float(item["bp{}".format(i)])
        colMap['bid_volume_{}'.format(i)] = float(item["bq{}".format(i)])
    return colMap

data = data.apply(lambda item:MyTickData(
                symbol="BTC",
                datetime=item.timestamp,
                exchange=Exchange.BINANCE,
                custom_field=(item['ap1']+item['ap2'])/2,
                **mapCol(item),
                gateway_name="DB",       
),axis=1)

engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol="BTC.BINANCE",
    interval="1m",
    start=datetime.datetime(2020,5,19),
    end=datetime.datetime(2021,5,22),
    rate=0.5/10000,
    slippage=5,
    size=.1,
    pricetick=5,
    capital=100000,
    mode=BacktestingMode.TICK,
)
engine.add_strategy(TestStrategy,{})
# engine.load_data()
engine.history_data = data
engine.run_backtesting()
df = engine.calculate_result()
engine.calculate_statistics()
# engine.show_chart()
