"""
AC countertrend strategy.

Buy pullbacks in a bull market; go all-in on each entry.

Rules
-----
Bull market: 40-day EMA > 80-day EMA.

Pullback (standard deviations below the 20-day high close):

    pullback = (highest_close_20 - close) / daily_std_40

where ``daily_std_40`` is the 40-day standard deviation of daily price
changes (percent returns).

Entry (flat only):
    - Bull market
    - Pullback >= ``min_pullback`` standard deviations
    - Full buying power (all-in)

Exit (when long):
    - Bear market (40-day EMA <= 80-day EMA) when ``exit_on_bear`` is True, or
    - Close above ``exit_ma``-day simple moving average, or
    - Close below stop loss (``stop_loss_pct`` below entry, default 15%), or
    - Position held for ``hold_period`` trading days, or
    - Last bar of the backtest
"""

import datetime

import pinkfish as pf


pf.DEBUG = False

default_options = {
    'use_adj': False,
    'use_cache': True,
    'margin': 1,
    'std_period': 40,
    'high_period': 20,
    'ema_fast': 40,
    'ema_slow': 80,
    'hold_period': 20,
    'min_pullback': 3.0,
    'exit_ma': 20,
    'stop_loss_pct': 0.15,
    'exit_on_bear': True,
}


class Strategy:

    def __init__(self, symbol, capital, start, end, options=default_options):

        self.symbol = symbol
        self.capital = capital
        self.start = start
        self.end = end
        self.options = options.copy()

        self.ts = None
        self.tlog = None
        self.dbal = None
        self.stats = None
        self.bars_held = 0

    def _algo(self):

        pf.TradeLog.cash = self.capital
        pf.TradeLog.margin = self.options['margin']
        hold_period = self.options['hold_period']
        min_pullback = self.options['min_pullback']
        stop_loss_pct = self.options.get('stop_loss_pct', 0.15)
        exit_on_bear = self.options.get('exit_on_bear', True)
        stop_loss = 0

        for i, row in enumerate(self.ts.itertuples()):

            date = row.Index.to_pydatetime()
            close = row.close
            end_flag = pf.is_last_row(self.ts, i)

            if self.tlog.shares > 0:
                self.bars_held += 1
                bear_exit = exit_on_bear and not row.bull
                above_ma = close > row.exit_ma
                hit_stop = stop_loss > 0 and close < stop_loss
                if (bear_exit
                        or above_ma
                        or hit_stop
                        or self.bars_held >= hold_period
                        or end_flag):
                    self.tlog.sell(date, close)
                    self.bars_held = 0
                    stop_loss = 0

            else:
                self.bars_held = 0
                if (row.bull
                        and row.pullback >= min_pullback
                        and row.daily_std > 0):
                    self.tlog.buy(date, close)
                    self.bars_held = 1
                    if stop_loss_pct < 1:
                        stop_loss = (1 - stop_loss_pct) * close

            self.dbal.append(date, close)

    def run(self):

        opts = self.options
        self.ts = pf.fetch_timeseries(self.symbol, use_cache=opts['use_cache'])
        self.ts = pf.select_tradeperiod(
            self.ts, self.start, self.end, use_adj=opts['use_adj'])

        self.ts['ema_fast'] = pf.EMA(self.ts, timeperiod=opts['ema_fast'])
        self.ts['ema_slow'] = pf.EMA(self.ts, timeperiod=opts['ema_slow'])
        self.ts['bull'] = self.ts['ema_fast'] > self.ts['ema_slow']

        self.ts['daily_std'] = (
            self.ts['close'].pct_change().rolling(opts['std_period']).std())

        self.ts['high_close'] = (
            self.ts['close'].rolling(opts['high_period']).max())

        self.ts['pullback'] = (
            (self.ts['high_close'] - self.ts['close']) / self.ts['daily_std'])

        self.ts['exit_ma'] = pf.SMA(self.ts, timeperiod=opts['exit_ma'])

        self.ts, self.start = pf.finalize_timeseries(
            self.ts, self.start, dropna=True,
            drop_columns=['open', 'high', 'low'])

        self.tlog = pf.TradeLog(self.symbol)
        self.dbal = pf.DailyBal()

        self._algo()
        self._get_logs()
        self._get_stats()

    def _get_logs(self):
        self.tlog = self.tlog.get_log()
        self.dbal = self.dbal.get_log(self.tlog)

    def _get_stats(self):
        self.stats = pf.stats(self.ts, self.tlog, self.dbal, self.capital)


def main():
    """Run a backtest with the same defaults as strategy.ipynb."""
    symbol = 'SPY'
    capital = 10000
    start = datetime.datetime(*pf.SP500_BEGIN)
    end = datetime.datetime.now()
    s = Strategy(symbol, capital, start, end)
    s.run()
    pf.print_full(s.stats)


if __name__ == '__main__':
    main()
