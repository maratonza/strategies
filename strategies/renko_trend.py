import pandas as pd

from lom.interface.strategy import IStrategy
from strategy.utils import indicators
from lom.model.constant import Interval, OrderSide


class RenkoTrend(IStrategy):
    def __init__(self, symbol: str, interval: Interval, renko_step=400):
        super().__init__(symbol, interval)
        self.renko_step = renko_step
        self.wallet_history = []

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)

        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)
        rdf = indicators.get_renko(df.timestamp, df.close, self.renko_step)

        df = df.merge(rdf, left_on='timestamp', right_on='timestamp', how='left')
        df = df.fillna(method="ffill")

        df = df.dropna()
        df = df.reset_index(drop=True)

        df['buy'] = df.is_green
        df['sell'] = ~df.is_green.astype(bool)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.wallet_history.append(self.wallet.balance)

        # Close long
        if position.quantity > 0 and df.sell.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity))

        # Close short
        if position.quantity < 0 and df.buy.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity))

        if 0 < len(df):
            # Open long
            if position.side is None and df.buy.iloc[-1]:
                quantity = round(self.wallet.available_balance * position.leverage * 0.93 / market_price, 3)
                self.trade.place_order(self.symbol, OrderSide.BUY, quantity)

            # Open short
            if position.side is None and df.sell.iloc[-1]:
                quantity = round(self.wallet.available_balance * position.leverage * 0.93 / market_price, 3)
                self.trade.place_order(self.symbol, OrderSide.SELL, quantity)
