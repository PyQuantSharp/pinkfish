"""
stategy
---------
"""

import pandas as pd
import matplotlib.pyplot as plt
import datetime
from talib.abstract import *

import pinkfish as pf

pf.DEBUG = False


class Strategy:

    def __init__(self, symbol, capital, start, end, use_adj=False,
                 period=7, max_positions=4):
        self.symbol = symbol
        self.capital = capital
        self.start = start
        self.end = end
        self.use_adj = use_adj
        self.period = period
        self.max_positions = max_positions
        
    def _algo(self):
        """ Algo:
            1. The SPY is above its 200-day moving average
            2. The SPY closes at a X-day low, buy some shares.
               If it falls further, buy some more, etc...
            3. If the SPY closes at a X-day high, sell your entire long position.
        """
        pf.TradeLog.cash = self.capital

        for i, row in enumerate(self.ts.itertuples()):

            date = row.Index.to_pydatetime()
            high = row.high; low = row.low; close = row.close; 
            end_flag = pf.is_last_row(self.ts, i)
            shares = 0

            # Sell Logic
            # First we check if an existing position in symbol should be sold
            #  - sell if price close sets a new period_high
            #  - sell if end of data

            if (self.tlog.num_open_trades() > 0
                  and (close == row.period_high
                       or end_flag)):

                # enter sell in trade log
                shares = self.tlog.sell(date, close)

            # Buy Logic
            # First we check to see if we have exceeded max_positions, if so do nothing
            #  - Buy if regime > 0 
            #            and price close sets a new period_low

            elif (self.tlog.num_open_trades() < self.max_positions
                and row.regime > 0
                and close == row.period_low):

                # calc number of shares
                buying_power = self.tlog.calc_buying_power(price=close)
                cash = buying_power / (self.max_positions - self.tlog.num_open_trades())
                shares = self.tlog.calc_shares(price=close, cash=cash)
                # enter buy in trade log
                self.tlog.buy(date, close, shares)

            if shares > 0:
                pf.DBG("{0} BUY  {1} {2} @ {3:.2f}".format(
                    date, shares, self.symbol, close))
            elif shares < 0:
                pf.DBG("{0} SELL {1} {2} @ {3:.2f}".format(
                    date, -shares, self.symbol, close))
            else:
                pass  # HOLD

            # record daily balance
            self.dbal.append(date, high, low, close)

    def run(self):
        self.ts = pf.fetch_timeseries(self.symbol)
        self.ts = pf.select_tradeperiod(self.ts, self.start,
                                         self.end, use_adj=False)

        # Add technical indicator: 200 sma regime filter
        self.ts['regime'] = \
            pf.CROSSOVER(self.ts, timeperiod_fast=1, timeperiod_slow=200)

        # Add technical indicator: X day high, and X day low
        period_high = pd.Series(self.ts.close).rolling(self.period).max()
        period_low = pd.Series(self.ts.close).rolling(self.period).min()
        self.ts['period_high'] = period_high
        self.ts['period_low'] = period_low
        
        self.ts, self.start = pf.finalize_timeseries(self.ts, self.start)
        
        self.tlog = pf.TradeLog(self.symbol)
        self.dbal = pf.DailyBal()

        self._algo()

    def get_logs(self, merge_trades=False):
        """ return DataFrames """
        self.rlog = self.tlog.get_log_raw()
        self.tlog = self.tlog.get_log(merge_trades)
        self.dbal = self.dbal.get_log(self.tlog)
        return self.rlog, self.tlog, self.dbal

    def get_stats(self):
        # call get_logs before calling this function
        stats = pf.stats(self.ts, self.tlog, self.dbal, self.capital)
        return stats

def summary(strategies, metrics):
    """ Stores stats summary in a DataFrame.
        stats() must be called before calling this function """
    index = []
    columns = strategies.index
    data = []
    # add metrics
    for metric in metrics:
        index.append(metric)
        data.append([strategy.stats[metric] for strategy in strategies])

    df = pd.DataFrame(data, columns=columns, index=index)
    return df

