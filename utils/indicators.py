import math

import pandas as pd
import talib


def get_renko(timestamps, close, step=50):
    prices = close
    first_brick = {
        'timestamp': timestamps.iloc[0],
        'renko_open': math.floor(prices.iloc[0] / step) * step,
        'renko_close': math.floor((prices.iloc[0] / step) + 1) * step
    }
    first_brick['is_green'] = first_brick['renko_close'] > first_brick['renko_open']
    bricks = [first_brick]
    for price, timestamp in zip(prices, timestamps):
        if price > (bricks[-1]['renko_close'] + step):
            step_mult = math.floor((price - bricks[-1]['renko_close']) / step)
            next_brick = {
                'timestamp': timestamp,
                'renko_open': bricks[-1]['renko_close'] if bricks[-1]['is_green'] else bricks[-1]['renko_close'] + step,
                'renko_close': bricks[-1]['renko_close'] + step_mult * step
            }
            next_brick['is_green'] = next_brick['renko_close'] > next_brick['renko_open']

            bricks += [next_brick]

        elif price < bricks[-1]['renko_close'] - step:
            step_mult = math.ceil((bricks[-1]['renko_close'] - price) / step)
            next_brick = {
                'timestamp': timestamp,
                'renko_open': bricks[-1]['renko_close'] - step if bricks[-1]['is_green'] else bricks[-1]['renko_close'],
                'renko_close': bricks[-1]['renko_close'] - (step_mult - 1) * step
            }
            next_brick['is_green'] = next_brick['renko_close'] > next_brick['renko_open']

            bricks += [next_brick]

        else:
            continue

    rdf = pd.DataFrame(bricks)
    rdf = rdf.drop(index=0)

    return rdf


def get_heikin_ashi_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    df['haclose'] = (df.open + df.high + df.low + df.close) / 4
    haopen = [(df.open.iloc[0] + df.close.iloc[0]) / 2]
    for index in range(1, len(df)):
        haopen.append((haopen[index - 1] + df.haclose.iloc[index - 1]) / 2)
    df['haopen'] = haopen
    df['hahigh'] = df[['high', 'haopen', 'haclose']].max(axis=1)
    df['halow'] = df[['low', 'haopen', 'haclose']].min(axis=1)

    return df


def get_std(close, length=20):
    std = close.rolling(length).std()

    return std


def get_smoothed_momentum(close, length=20):
    mom = get_momentum(close)
    s_mom = get_sma(mom)

    return s_mom


def get_atr(high, low, close, length=20):
    atr = talib.ATR(high, low, close, timeperiod=length)

    return atr


def get_macd(close, fast=12, slow=26, signal=9):
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal)

    return macd, macd_signal, macd_hist


def get_momentum(close, length=10):
    mom = talib.MOM(close, length)

    return mom


def get_rsi(close, length=14):
    rsi = talib.RSI(close, length)

    return rsi


def get_bb(close):
    upper, middle, lower = talib.BBANDS(close, timeperiod=20)

    return upper, middle, lower


def get_sma(close, length=9):
    sma = talib.SMA(close, timeperiod=length)

    return sma


def get_ema(close, length=9):
    sma = talib.EMA(close, timeperiod=length)

    return sma


def get_ichimoku(close, high, low, conversion_line_length=9, base_line_length=26,
                 leading_span_b=52, lagging_span_length=26):
    period9_high = high.rolling(window=conversion_line_length).max()
    period9_low = low.rolling(window=conversion_line_length).min()
    conversion_line = (period9_high + period9_low) / 2

    period26_high = high.rolling(window=base_line_length).max()
    period26_low = low.rolling(window=base_line_length).min()
    base_line = (period26_high + period26_low) / 2

    leading_span_a = ((conversion_line + base_line) / 2).shift(26)

    period52_high = high.rolling(window=leading_span_b).max()
    period52_low = low.rolling(window=leading_span_b).min()
    leading_span_b = ((period52_high + period52_low) / 2).shift(26)

    lagging_span = close.shift(-lagging_span_length)

    return conversion_line, base_line, leading_span_a, leading_span_b, lagging_span
