from lom.interface.strategy import IStrategy
from lom.model.constant import Interval, OrderSide
from strategy.utils import technical_events
from strategy.utils import indicators


class RsiDivergence(IStrategy):
    def __init__(self, symbol: str, interval: Interval, risk_per_reward=1.5, div_lookback=10):
        super().__init__(symbol, interval)
        self.risk_per_reward = risk_per_reward
        self.div_lookback = div_lookback
        self.wallet_history = []

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)
        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)

        df['rsi'] = indicators.get_rsi(df['close'])
        df = df.dropna().reset_index(drop=True)
        df['hh_div'] = technical_events.find_hh_divergence(df.close, df.rsi, self.div_lookback)
        df['ll_div'] = technical_events.find_ll_divergence(df.close, df.rsi, self.div_lookback)

        df['sell'] = df.hh_div
        df['buy'] = df.ll_div

        df = df.dropna()
        df = df.reset_index(drop=True)

        plot_cols = ['rsi']
        self.set_plot_columns(plot_cols)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    # THIS HAS TO CHANGE
    def next(self):
        df = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)
        position = self.trade.get_position(self.symbol)
        self.handle_orders(position)
        self.wallet_history.append(self.wallet.balance)

        if position.side is None:
            quantity = round(self.wallet.available_balance * position.leverage * 0.95 / market_price, 3)
            # open long
            if df.buy.iloc[-1]:
                self.wallet_history.append(self.wallet.balance)
                entry_price = df.close.iloc[-1]
                tp = entry_price * 1.01
                sl = entry_price - (tp - entry_price) / self.risk_per_reward

                self.trade.place_order(self.symbol, OrderSide.BUY, quantity)
                self.trade.place_order(self.symbol, OrderSide.SELL, quantity, price=tp)
                if position.side is not None:
                    self.trade.place_order(self.symbol, OrderSide.SELL, quantity, stop_price=sl)

            # open short
            if df.sell.iloc[-1]:
                self.wallet_history.append(self.wallet.balance)
                entry_price = df.close.iloc[-1]
                tp = entry_price * 0.99
                sl = entry_price + (entry_price - tp) / self.risk_per_reward

                self.trade.place_order(self.symbol, OrderSide.SELL, quantity)
                self.trade.place_order(self.symbol, OrderSide.BUY, quantity, price=tp)
                if position.side is not None:
                    self.trade.place_order(self.symbol, OrderSide.BUY, quantity, stop_price=sl)

    def handle_orders(self, position):
        if position.quantity == 0:
            self.trade.cancel_open_orders()
