from typing import List
import pandas as pd

from lom.interface.strategy import IStrategy
from lom.model.constant import Interval, OrderSide
from strategy.utils import indicators


class IchimokuIdeal(IStrategy):
    def __init__(self, symbol: str, interval: Interval, sl_lookback: int = 5, conversion_line_length=9,
                 base_line_length=26, leading_span_b=52, lagging_span_length=26):
        super().__init__(symbol, interval)
        self.sl_lookback = sl_lookback
        self.conversion_line_length = conversion_line_length
        self.base_line_length = base_line_length
        self.leading_span_b = leading_span_b
        self.lagging_span_length = lagging_span_length
        self.wallet_history = []

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)
        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)

        df['conversion_line'], df['base_line'], df['leading_span_a'], df['leading_span_b'], \
            df['lagging_span'] = indicators.get_ichimoku(df['close'], df['high'], df['low'])

        bdf = pd.DataFrame()
        bdf['price_above_kumo'] = (df.close > df.leading_span_a) & (df.close > df.leading_span_b)
        bdf['conv_above_kumo'] = (df.conversion_line >= df.leading_span_a) & (df.conversion_line >= df.leading_span_b)
        bdf['conv_above_base'] = (df.conversion_line > df.base_line)
        bdf['is_kumo_green'] = (df.leading_span_a.shift(-26) >= df.leading_span_b.shift(-26))
        bdf['leading_a_bull'] = (df.leading_span_a.shift(-25) >= df.leading_span_a.shift(-26))
        bdf['leading_b_bull'] = (df.leading_span_b.shift(-25) >= df.leading_span_b.shift(-26))
        bdf['base_bull'] = (df.base_line >= df.base_line.shift(1))
        bdf['conv_bull'] = (df.conversion_line >= df.conversion_line.shift(1))
        bdf['lag_above_leading_a'] = (
                df.lagging_span.shift(self.lagging_span_length) > df.leading_span_a.shift(self.lagging_span_length))
        bdf['lag_above_leading_b'] = (
                df.lagging_span.shift(self.lagging_span_length) > df.leading_span_a.shift(self.lagging_span_length))
        bdf['price_above_future_kumo'] = (df.high > df.leading_span_a.shift(-26).rolling(26).max()) & \
                                         (df.high > df.leading_span_b.shift(-26).rolling(26).max())
        bdf['lag_above_past_prices'] = (
                df.lagging_span.shift(self.lagging_span_length) > df.high.rolling(self.lagging_span_length).max())
        ## not using lag_above_past_prices at the moment

        sdf = pd.DataFrame()
        sdf['price_below_kumo'] = (df.close < df.leading_span_a) & (df.close < df.leading_span_b)
        sdf['conv_below_kumo'] = (df.conversion_line <= df.leading_span_a) & (df.conversion_line <= df.leading_span_b)
        sdf['conv_below_base'] = (df.conversion_line < df.base_line)
        sdf['is_kumo_red'] = (df.leading_span_a.shift(-26) <= df.leading_span_b.shift(-26))
        sdf['leading_a_bear'] = (df.leading_span_a.shift(-25) <= df.leading_span_a.shift(-26))
        sdf['leading_b_bear'] = (df.leading_span_b.shift(-25) <= df.leading_span_b.shift(-26))
        sdf['base_bear'] = (df.base_line <= df.base_line.shift(1))
        sdf['conv_bear'] = (df.conversion_line <= df.conversion_line.shift(1))
        sdf['lag_below_leading_a'] = (
                df.lagging_span.shift(self.lagging_span_length) < df.leading_span_a.shift(self.lagging_span_length))
        sdf['lag_below_leading_b'] = (
                df.lagging_span.shift(self.lagging_span_length) < df.leading_span_a.shift(self.lagging_span_length))
        sdf['price_below_future_kumo'] = (df.low < df.leading_span_a.shift(-26).rolling(26).min()) & \
                                         (df.low < df.leading_span_b.shift(-26).rolling(26).min())
        sdf['lag_below_past_prices'] = (
                df.lagging_span.shift(self.lagging_span_length) < df.high.rolling(self.lagging_span_length).min())
        ## not using lag_below_past_prices at the moment

        df['buy'] = bdf.price_above_kumo & bdf.conv_above_kumo & bdf.conv_above_base & bdf.is_kumo_green & \
                    bdf.leading_a_bull & bdf.leading_b_bull & bdf.base_bull & bdf.conv_bull & bdf.lag_above_leading_a & \
                    bdf.lag_above_leading_b & bdf.price_above_future_kumo
        df['sell'] = sdf.price_below_kumo & sdf.conv_below_kumo & sdf.conv_below_base & sdf.is_kumo_red & \
                     sdf.leading_a_bear & sdf.leading_b_bear & sdf.base_bear & sdf.conv_bear & sdf.lag_below_leading_a & \
                     sdf.lag_below_leading_b & sdf.price_below_future_kumo

        df['close_buy'] = df.conversion_line < df.base_line
        df['close_sell'] = df.conversion_line > df.base_line

        df = df.dropna()
        df = df.reset_index(drop=True)

        plot_cols = [('conversion_line', 'b'),
                     ('base_line', 'r'),
                     ('leading_span_a', 'g'),
                     ('leading_span_b', 'tab:red'),
                     ('lagging_span', 'tab:green')]
        self.set_plot_columns(plot_cols)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.handle_orders(position)
        self.wallet_history.append(self.wallet.balance)

        if 0 < len(df):
            # Close long
            if position.side == 1 and df.close_buy.iloc[-1]:
                self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity))
            # Close short
            if position.side == -1 and df.close_sell.iloc[-1]:
                self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity))

            self.handle_orders(position)

            if position.side is None:
                quantity = self.wallet.available_balance / df.close.iloc[-1] * 0.95
                # Open long
                if df.buy.iloc[-1]:
                    sl = df.low.rolling(self.sl_lookback).min().iloc[-1]

                    self.trade.place_order(self.symbol, OrderSide.BUY, quantity)
                    self.trade.place_order(self.symbol, OrderSide.SELL, quantity, stop_price=sl)

                # Open short
                if df.sell.iloc[-1]:
                    sl = df.high.rolling(self.sl_lookback).max().iloc[-1]

                    self.trade.place_order(self.symbol, OrderSide.SELL, quantity)
                    self.trade.place_order(self.symbol, OrderSide.BUY, quantity, stop_price=sl)

    def handle_orders(self, position):
        if position.quantity == 0:
            self.trade.cancel_open_orders()
