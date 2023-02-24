from lom.interface.strategy import IStrategy
from lom.model.constant import Interval, OrderSide


class SmaCrossStrategy(IStrategy):
    def __init__(self, symbol: str, interval: Interval, fast_length: int = 10, slow_length: int = 20):
        super().__init__(symbol, interval)
        self.__fast_length = fast_length
        self.__slow_length = slow_length

    def prepare(self):
        self.trade.set_leverage(self.symbol, 1)

        df = self.data.get_ohlcv_source_dataframe(self.symbol, self.interval)
        df['fast'] = df.close.rolling(self.__fast_length).mean()
        df['slow'] = df.close.rolling(self.__slow_length).mean()

        df['previous_fast'] = df.fast.shift(1)
        df['previous_slow'] = df.slow.shift(1)

        df['buy'] = (df.previous_fast < df.previous_slow) & (df.slow < df.fast)
        df['sell'] = (df.previous_slow < df.previous_fast) & (df.fast < df.slow)

        df = df.dropna()
        df = df.reset_index(drop=True)

        self.data.set_ohlcv_source_dataframe(self.symbol, self.interval, df)

    def next(self):
        ohlcv_dataframe = self.data.get_ohlcv_dataframe(self.symbol, self.interval)
        market_price = self.data.get_market_price(self.symbol)

        if 0 < len(ohlcv_dataframe):
            # buy signal
            if ohlcv_dataframe.buy.iloc[-1]:
                # close short position
                position = self.trade.get_position(self.symbol)
                if position.quantity < 0:
                    self.trade.place_order(self.symbol, OrderSide.BUY, abs(position.quantity))

                # open long position
                available_balance = self.wallet.available_balance
                quantity = round(available_balance * position.leverage * 0.95 / market_price, 3)
                self.trade.place_order(self.symbol, OrderSide.BUY, quantity)

            # sell signal
            if ohlcv_dataframe.sell.iloc[-1]:
                # close long position
                position = self.trade.get_position(self.symbol)
                if 0 < position.quantity:
                    self.trade.place_order(self.symbol, OrderSide.SELL, abs(position.quantity))

                # open short position
                available_balance = self.wallet.available_balance
                quantity = round(available_balance * position.leverage * 0.95 / market_price, 3)
                self.trade.place_order(self.symbol, OrderSide.SELL, quantity)
