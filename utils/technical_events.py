import pandas as pd
import numpy as np


def find_hh_divergence(df1, df2, lookback):
    tdf = pd.DataFrame()

    # Find index of HHs for each df and save the index            (hh1_1 -> 1st Highest High for df 1)
    tdf['hh1_1'] = df1.rolling(lookback).apply(lambda x: x.idxmax())
    tdf['hh2_1'] = df1.rolling(lookback).apply(lambda x: list(df1).index(-np.sort(-x)[1]))

    tdf['hh1_2'] = tdf['hh1_1'].map(df2)
    tdf['hh2_2'] = tdf['hh2_1'].map(df2)

    tdf['hh_div'] = (tdf.hh1_2 > 70) & (tdf.hh2_2 > 70) & (tdf.hh2_1 < tdf.hh1_1) & (tdf.hh2_2 > tdf.hh1_2)

    return tdf['hh_div']


def find_ll_divergence(df1, df2, lookback):
    tdf = pd.DataFrame()

    # Find index of LLs for each df and save the index            (ll1_1 -> 1st Lowest Low for df 1)
    tdf['ll1_1'] = df1.rolling(lookback).apply(lambda x: x.idxmin())
    tdf['ll2_1'] = df1.rolling(lookback).apply(lambda x: list(df1).index(np.sort(x)[1]))

    tdf['ll1_2'] = tdf['ll1_1'].map(df2)
    tdf['ll2_2'] = tdf['ll2_1'].map(df2)

    tdf['ll_div'] = (tdf.ll1_2 < 30) & (tdf.ll2_2 < 30) & (tdf.ll2_1 > tdf.ll1_1) & (tdf.ll2_2 < tdf.ll1_2)

    return tdf['ll_div']
