from lom.interface.strategy import IStrategy

from strategy.strategies.super_guppy import SuperGuppy
from strategy.utils import indicators
from lom.model.constant import Interval, OrderSide, PositionSide
from strategy.utils import technical_events


class SuperGuppySlope(SuperGuppy):
    def __init__(self, symbol: str, interval: Interval, slope_ema_length=3):
        super().__init__(symbol, interval)
        self.slope_ema_length = slope_ema_length
        self.wallet_history = []

    def prepare(self):
        super(SuperGuppySlope, self).prepare()
        df = super(SuperGuppySlope, self).data.get_ohlcv_dataframe(self.symbol, self.interval)
        df[f'ema'] = indicators.get_ema(df.close, self.slope_ema_length)
        df['pos_slope'] = df.ema >= df.ema.shift(1)

        df = df.dropna()
        df = df.reset_index(drop=True)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.handle_orders(position)

        # Close long
        if position.side == PositionSide.LONG and not df.pos_slope.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity))
        # Close short
        if position.side == PositionSide.SHORT and df.pos_slope.iloc[-1]:
            self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity))

        if position.side is None:
            quantity = self.wallet.available_balance / df.close.iloc[-1] * 0.95
            # Open long
            if df.buy.iloc[-1]:
                self.wallet_history.append(self.wallet.available_balance)
                self.trade.place_order(self.symbol, OrderSide.BUY, quantity)

            # Open short
            elif df.sell.iloc[-1]:
                self.wallet_history.append(self.wallet.available_balance)
                self.trade.place_order(self.symbol, OrderSide.BUY, quantity)

    def handle_orders(self, position):
        if position.quantity == 0:
            self.trade.cancel_open_orders()
