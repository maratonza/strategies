import math

from lom.interface.strategy import IStrategy
from lom.model.constant import Interval, OrderSide, PositionSide

from utils import indicators


class HeikinAshiTrend(IStrategy):
    def __init__(self, symbol: str, interval: Interval, sl_lookback: int = 10):
        super().__init__(symbol, interval)
        self.sl_lookback = sl_lookback
        self.wallet_history = []

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)

        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)
        df = indicators.get_heikin_ashi_dataframe(df)

        df['buy'] = df.haopen == df.halow
        df['close_buy'] = df.haopen > df.haclose
        df['lsl'] = df.close.rolling(self.sl_lookback).min()

        df['sell'] = df.haopen == df.hahigh
        df['close_sell'] = df.haopen < df.haclose
        df['ssl'] = df.close.rolling(self.sl_lookback).max()

        df = df[100:]
        df = df.dropna()
        df = df.reset_index(drop=True)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.handle_orders(position)
        self.wallet_history.append(self.wallet.balance)

        # Close long
        if PositionSide.LONG == position.side and df.close_buy.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity))
            self.trade.cancel_open_orders()

        # Close short
        if PositionSide.SHORT == position.side and df.close_sell.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity))
            self.trade.cancel_open_orders()

        if position.side is None:
            quantity = round(self.wallet.available_balance * position.leverage * 0.95 / market_price, 3)

            # open long
            if df.buy.iloc[-1]:
                sl = df.lsl.iloc[-1]
                stop_price = sl if not (math.isnan(sl) or sl == market_price) else 0.995 * market_price

                self.trade.place_order(self.symbol, OrderSide.BUY, abs(quantity))
                # self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity), stop_price=stop_price)

            # open short
            if df.sell.iloc[-1]:
                sl = df.ssl.iloc[-1]
                stop_price = sl if not (math.isnan(sl) or sl == market_price) else 1.005 * market_price

                self.trade.place_order(self.symbol, OrderSide.SELL, abs(quantity))
                # self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity), stop_price=stop_price)

    def handle_orders(self, position):
        if position.quantity == 0:
            self.trade.cancel_open_orders()
