from typing import List

from lom.interface.strategy import IStrategy
from lom.model.constant import Interval, OrderSide
from strategy.utils import indicators


class BbMaTrend(IStrategy):
    def __init__(self, symbol: str, interval: Interval, ma_length: int = 1000, risk_per_reward=1):
        super().__init__(symbol, interval)
        self.__ma_length = ma_length
        self.risk_per_reward = risk_per_reward

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)

        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)
        df['ma'] = indicators.get_sma(df.close, length=self.__ma_length)
        df['bb_upper'], df['bb_mid'], df['bb_lower'] = indicators.get_bb(df.close)

        df['trend'] = df['close'] > df['ma']

        df['buy'] = df.trend & (df.close <= df.bb_lower)
        df['sell'] = (~df.trend) & (df.close >= df.bb_upper)

        df = df.dropna()
        df = df.reset_index(drop=True)

        plot_cols = ['bb_upper', 'bb_lower']
        self.set_plot_columns(plot_cols)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.handle_orders(position)

        if 0 < len(df):
            quantity = round(self.wallet.available_balance * position.leverage * 0.95 / market_price, 3)
            if position.side is None:
                # open long
                if df.buy.iloc[-1]:
                    entry_price = market_price
                    tp = df.bb_upper.iloc[-1]
                    sl = entry_price - (tp - entry_price) / self.risk_per_reward

                    self.trade.place_order(self.symbol, OrderSide.BUY, abs(quantity))
                    self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity), price=tp)
                    if abs(position.quantity) > 0:
                        self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity), stop_price=sl)

                # open short
                if df.sell.iloc[-1]:
                    entry_price = market_price
                    tp = df.bb_lower.iloc[-1]
                    sl = entry_price + (entry_price - tp) / self.risk_per_reward

                    self.trade.place_order(self.symbol, OrderSide.SELL, abs(quantity))
                    self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity), price=tp)
                    if abs(position.quantity) > 0:
                        self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity), stop_price=sl)

    def handle_orders(self, position):
        if position.quantity == 0:
            self.trade.cancel_open_orders()
