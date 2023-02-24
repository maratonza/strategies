from abc import ABC
import pandas as pd
import numpy as np

from lom.interface.strategy import IStrategy
from strategy.utils import indicators
from lom.model.constant import Interval, OrderSide
from strategy.utils import technical_events


class SuperGuppy(IStrategy, ABC):
    def __init__(self, symbol: str, interval: Interval):
        super().__init__(symbol, interval)

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)
        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)

        for length in range(3, 24, 2):
            df[f'ema{length}'] = indicators.get_ema(df.close, length)

        for length in range(25, 71, 3):
            df[f'ema{length}'] = indicators.get_ema(df.close, length)

        df = df.dropna()

        df['fast_trend'] = self.check_parallelism(df[[f'ema{i}' for i in range(3, 24, 2)]])
        df['slow_trend'] = self.check_parallelism(df[[f'ema{i}' for i in range(25, 71, 3)]])

        df['buy'] = df.slow_trend + df.fast_trend == 2
        df['sell'] = df.slow_trend + df.fast_trend == -2

        df = df.dropna()
        df = df.reset_index(drop=True)

        plot_cols = [(f'ema{i}', 'b') for i in range(3, 24, 2)] + \
                    [(f'ema{i}', 'b') for i in range(25, 71, 3)]
        self.set_plot_columns(plot_cols)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def check_parallelism(self, df):
        diff = df.diff(axis=1)
        c1 = diff.fillna(-1).lt(0).all(1)  # Check if all differences are negative
        c2 = diff.fillna(1).ge(1).all(1)  # Check if all differences are positive
        df['trend'] = np.select([c1, c2], [1, -1], 0)

        return df['trend']
