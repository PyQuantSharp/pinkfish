"""
fetch
---------
Retrive time series data
"""

import sys
import pandas as pd
import pandas_datareader.data as pdr
from pandas_datareader._utils import RemoteDataError
import datetime
import os
import pinkfish as pf


#####################################################################
# TIMESERIES (fetch, select, finalize)

def _get_cache_dir(dir_name):
    """ returns the path to the cache_dir """
    base_dir = ''
    try:
        conf = pf.read_config()
        base_dir = conf['base_dir']
    except:
        pass
    finally:
        dir_name = os.path.join(base_dir, dir_name)

    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name

def _adj_column_names(ts):
    """
    ta-lib expects columns to be lower case; to be consistent,
    change date index
    """
    ts.columns = [col.lower().replace(' ','_') for col in ts.columns]
    ts.index.names = ['date']
    return ts

def fetch_timeseries(symbol, dir_name='data', use_cache=True, from_year=None):
    """
    Read time series data. Use cached version if it exists and
    use_cache is True, otherwise retrive, cache, then read.
    """
    if from_year is None:
        from_year = 1900 if not sys.platform.startswith('win') else 1971

    # yahoo finance uses '-' where '.' is used in symbol names
    symbol = symbol.replace('.', '-')
    symbol = symbol.upper()

    # pinkfish allows the use of a suffix starting with a '_',
    # like SPY_SHRT, so extract the symbol
    symbol = symbol.split('_')[0]

    timeseries_cache = os.path.join(_get_cache_dir(dir_name), symbol + '.csv')

    if os.path.isfile(timeseries_cache) and use_cache:
        pass
    else:
        ts = pdr.DataReader(symbol, 'yahoo', start=datetime.datetime(from_year, 1, 1))
        ts.to_csv(timeseries_cache, encoding='utf-8')

    ts = pd.read_csv(timeseries_cache, index_col='Date', parse_dates=True)
    ts = _adj_column_names(ts)
    return ts

def _adj_prices(ts):
    """ Back adjust prices relative to adj_close for dividends and splits """
    ts['open'] = ts['open'] * ts['adj_close'] / ts['close']
    ts['high'] = ts['high'] * ts['adj_close'] / ts['close']
    ts['low'] = ts['low'] * ts['adj_close'] / ts['close']
    ts['close'] = ts['close'] * ts['adj_close'] / ts['close']
    return ts

def select_tradeperiod(ts, start, end, use_adj=False):
    """
    Select a time slice of the data to trade from ts.
    Back date a year to allow time for long term indicators,
    e.g. 200sma is become valid
    """
    if use_adj:
        _adj_prices(ts)

    if start < ts.index[0]: start = ts.index[0]
    if end > ts.index[-1]: end = ts.index[-1]
    ts = ts[start - datetime.timedelta(365):end]

    return ts

def finalize_timeseries(ts, start):
    """ Drop all rows that have nan column values
        Set timeseries to begin at start
    """
    ts = ts.dropna()
    ts = ts[start:]
    start = ts.index[0]
    return ts, start

#####################################################################
# CACHE SYMBOLS (remove, update, get_symbol_metadata)

def _difference_in_years(start, end):
    """ calculate the number of years between two dates """
    diff  = end - start
    diff_in_years = (diff.days + diff.seconds/86400)/365.2425
    return diff_in_years

def remove_cache_symbols(symbols=None, dir_name='data'):
    """
    Remove cached timeseries for list of symbols.
    If symbols is None, remove all timeseries.
    Filter out any symbols prefixed with '__'
    """
    cache_dir = _get_cache_dir(dir_name)

    if symbols:
        # in case user forgot to put single symbol in list
        if not isinstance(symbols, list):
            symbols = [symbols]
        filenames = [symbol.upper() + '.csv' for symbol in symbols]
    else:
        filenames = [f for f in os.listdir(cache_dir) if f.endswith('.csv')]

    # filter out any filename prefixed with '__'
    filenames = [f for f in filenames if not f.startswith('__')]

    print('removing symbols:')
    for i, f in enumerate(filenames):
        symbol = os.path.splitext(f)[0]
        print(symbol + ' ', end='')
        if i % 10 == 0 and i != 0: print()

        filepath = os.path.join(cache_dir, f)
        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            print('\n({} not found)'.format(f))
    print()

def update_cache_symbols(symbols=None, dir_name='data', from_year=None):
    """
    Update cached timeseries for list of symbols.
    If symbols is None, update all timeseries.
    Filter out any filename prefixed with '__'
    """
    cache_dir = _get_cache_dir(dir_name)

    if symbols:
        # in case user forgot to put single symbol in list
        if not isinstance(symbols, list):
            symbols = [symbols]
    else:
        filenames = ([f for f in os.listdir(cache_dir)
                     if f.endswith('.csv') and not f.startswith('__')])
        symbols = [os.path.splitext(filename)[0] for filename in filenames]

    # make symbol names uppercase
    symbols = [symbol.upper() for symbol in symbols]

    print('updating symbols:')
    for i, symbol in enumerate(symbols):
        print(symbol + ' ', end='')
        if i % 10 == 0 and i != 0: print()

        try:
            fetch_timeseries(symbol, dir_name=dir_name, use_cache=False,
                             from_year=from_year)
        except RemoteDataError as e:
            print('\n({})'.format(e))
        except Exception as e:
            print('\n({})'.format(e))
    print()

def get_symbol_metadata(symbols=None, dir_name='data', from_year=None):
    """
    Get symbol metadata for list of symbols.
    If symbols is None, get do for all timeseries.
    Filter out any filename prefixed with '__'
    """

    cache_dir = _get_cache_dir(dir_name)

    if symbols:
        # in case user forgot to put single symbol in list
        if not isinstance(symbols, list):
            symbols = [symbols]
    else:
        filenames = ([f for f in os.listdir(cache_dir)
                     if f.endswith('.csv') and not f.startswith('__')])
        symbols = [os.path.splitext(filename)[0] for filename in filenames]

    # make symbol names uppercase
    symbols = [symbol.upper() for symbol in symbols]

    l = []
    for i, symbol in enumerate(symbols):
        try:
            ts = pf.fetch_timeseries(symbol, dir_name=dir_name, use_cache=True,
                                     from_year=from_year) 
            start = ts.index[0].to_pydatetime()
            end = ts.index[-1].to_pydatetime()
            num_years = _difference_in_years(start, end)
            start = start.strftime('%Y-%m-%d')
            end = end.strftime('%Y-%m-%d')
            t = (symbol, start, end, num_years)
            l.append(t)
        except RemoteDataError as e:
            print('\n({})'.format(e))
        except Exception as e:
            print('\n({})'.format(e))
    columns = ['symbol', 'start_date', 'end_date', 'num_years']
    df = pd.DataFrame(l, columns=columns)
    return df
