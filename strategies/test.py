from vnpy.app.cta_strategy import (
    CtaTemplate,
    TickData,
    TradeData,
    OrderData,
)
import random

class TestStrategy(CtaTemplate):

    def on_init(self):
        print("test strategy init")
        self.load_tick(0)
    
    def on_start(self):
        print("test strategy start")

    def on_tick(self,tick:TickData):

        if self.pos == 0:
            if random.randint(0,10)>5:
                self.buy(tick.ask_price_1*1.1,0.1)
            else:
                self.sell(tick.bid_price_1/1.1,0.1)
        elif self.pos>0:
            self.sell(tick.bid_price_1/1.1,0.1)
        else:
            self.buy(tick.ask_price_1*1.1,0.1)

    def on_trade(self,trade:TradeData):
        self.put_event()

    