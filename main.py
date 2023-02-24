import os
import sys

import pandas as pd
from matplotlib import pyplot as plt
from tabulate import tabulate

from defenitions import CANDLES_DIR
from lom.local.data import LocalData
from lom.local.market import LocalMarket
from lom.local.pair import LocalPair
from lom.local.wallet import LocalWallet
from lom.model.constant import Interval
from lom.model.position import Position
from lom.util.performance_measures import PerformanceMeasures
from strategies.sma_cross import SmaCrossStrategy
from strategies.ha_trend import HeikinAshiTrend
from strategies.renko_trend import RenkoTrend
from strategies.bb_ma_trend import BbMaTrend
from strategy.strategies.ichimoku_trend import IchimokuIdeal
from strategy.strategies.rsi_divergence import RsiDivergence
from strategy.strategies.super_guppy_cross import SuperGuppyCross
from strategy.strategies.super_guppy_slope import SuperGuppySlope

sys.path.append("..")  # Adds higher directory to python modules path.

if '__main__' == __name__:
    symbol = 'BTC-USDT'
    interval = Interval.DAY1
    sdf = pd.read_csv(os.path.join(CANDLES_DIR, symbol, '1d.csv'))[:485]
    sdf.timestamp = sdf.timestamp / 1000
    btcusdt = LocalPair(symbol=symbol, price_precision=2, quantity_precision=3, interval=interval, dataframe=sdf)

    data = LocalData([btcusdt])
    wallet = LocalWallet(initial_capital=1000)
    market = LocalMarket(data, wallet)

    # strategy = RenkoTrend(symbol, interval)
    # strategy = HeikinAshiTrend(symbol, interval)
    # strategy = BbMaTrend(symbol, interval)
    # strategy = RsiDivergence(symbol, interval)
    # strategy = IchimokuIdeal(symbol, interval)
    # strategy = SmaCrossStrategy(symbol, interval)
    strategy = SuperGuppyCross(symbol, interval)
    # strategy = SuperGuppySlope(symbol, interval)
    positions = market.backtest(strategy, show_tqdm=True, plot_backtest=False,
                                start_date='2020-1-1')

    headers = ['OPEN DATETIME', 'CLOSE DATETIME', 'SYMBOL', 'SIDE', 'LEVERAGE', 'TRADED QUANTITY', 'TRADED MARGIN',
               'OPEN PRICE', 'CLOSE PRICE', 'FEE', 'REALIZED PNL', 'PNL %', 'RUN-UP', 'RUN-UP %', 'DRAW-DOWN',
               'DRAW-DOWN %']
    values = [position.to_list() for position in positions]
    table = tabulate(values, headers=headers)
    print(table)

    performance_measures = PerformanceMeasures(strategy.interval, positions)
    print(performance_measures)
    print()

    data = pd.DataFrame(strategy.wallet_history)

    plt.figure()
    plt.plot(data, label='wallet')
    plt.legend()
    plt.show()

    # print(data)
