# zipline run --bundle custom-csvdir-bundle -s 2007-08-01 -e 2020-05-01 -f C:\Users\jloss\PyCharmProjects\zipline_algo\beta\beta_algo_JL.py

# --------------------------------------------------------------------------------------------------
# Module Imports

# todo: interactive brokers tick data
# todo: write function to download, process, and register custom-csvdir-bundle
# todo: ask Denis for other strategy logic (going short, etc)

# todo: csv headers:
# todo:  date	  open	  high	   low	  close	  volume    dividend	split
# todo: 8/1/2007  124.36  125.46  122.88  123.26   264550   	0	        1



import inspect, warnings
import os, sys, logging
from datetime import datetime as dt
import pandas as pd
import pandas_datareader as pdr
from pandas_datareader.yahoo import daily
from pandas_datareader.yahoo.actions import YahooSplitReader
from pandas_datareader.yahoo import actions as pdrActions
from collections import OrderedDict

import zipline
from zipline.api import *
from zipline.data.bundles import register
from zipline.data.bundles.csvdir import csvdir_equities
import zipline.data.bundles as zdb
# from zipline.data.bundles import ingest, csvdir

from fnCommon import setLogging
from fnTradingCritera import setPandas

warnings.simplefilter(action='ignore',category = UserWarning)
# quandl_api_key='PPzVtduYsyxVgf9z1WGo'

# --------------------------------------------------------------------------------------------------
# setup logging

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

LOGGING_DIRECTORY = os.path.join('C:\\', 'Users\\jloss\\PyCharmProjects\\zipline_algo\\beta\\', 'logs\\', dt.today().strftime('%Y-%m-%d'))

LOG_FILE_NAME = os.path.basename(__file__)


# --------------------------------------------------------------------------------------------------
# get simulation start date from the earliest possible data point for ticker SH

from beta.beta_config import config

def fnGetStartDate(ticker='SH'):

    pdr.yahoo.daily.YahooDailyReader.default_start_date = 2000

    print('\n First row of data for ticker: {}: \n'.format(ticker), pdrActions.YahooDailyReader(ticker, get_actions=False, adjust_price=False, adjust_dividends=False).read().head(1))

    firstDate = pdrActions.YahooDailyReader(ticker, get_actions=False, adjust_price=False, adjust_dividends=False).read().index[0].tz_localize('UTC')
    print('\nEarliest data point available:', pd.to_datetime(firstDate).strftime('%Y-%m-%d'), '\n')

    endDate = pd.to_datetime(config.get('end_date'), format = '%Y%m%d').tz_localize('UTC')
    return firstDate, endDate


# --------------------------------------------------------------------------------------------------
# download ticker data from yahoo

def fnDownloadCSVData(tickers=None, start=None, end=None):
    data = OrderedDict()

    if not tickers:
        tickers=['SH','SPY']
    else:
        tickers = tickers

    for symbol in tickers:
        if symbol == 'SH':
            data[symbol] = pdrActions.YahooDailyReader('{}'.format(symbol),  start=start, end=end,
                                                       get_actions=False, adjust_price=False, adjust_dividends=False).read()
        else:
            data[symbol] = pdrActions.YahooDailyReader('{}'.format(symbol),  start=start, end=end,
                                                       get_actions=True, adjust_price=False, adjust_dividends=False).read()
        data[symbol].index.name='date'
        # data[symbol].reset_index(inplace=True)

        data[symbol].rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume',},inplace=True)
        data[symbol]['split'] = 1

        if symbol == 'SPY':
            data[symbol].rename(columns={'Dividends':'dividend'}, inplace=True)
            data[symbol]['dividend'].fillna(0, inplace=True)
        if symbol == 'SH':
            data[symbol]['dividend'] = 0
            data[symbol].loc[data[symbol].index=='2016-06-24', 'split']=2

        data[symbol] = data[symbol][['open','high','low','close','volume','dividend','split']]

        data[symbol].to_csv('C:\\zipline_algo\\beta\\data\\daily\\{}.csv'.format(symbol))
        print('Ticker {} loaded: \n'.format(symbol), data[symbol].head(),'\n')

    return


# --------------------------------------------------------------------------------------------------
# process custom benchmark data for zipline backtest
# This addresses common benchmark returns issues with the Zipline API
#
# original repo located here:
# https://github.com/cemal95/benchmark-returns-for-zipline

def fnGetBenchmarkReturns(symbol='SPY'):

    benchmarkData = 'C:\\zipline_algo\\beta\\data\\daily\\{}.csv'.format(symbol)
    df = pd.read_csv(benchmarkData,index_col=['date'],parse_dates=['date']).tz_localize('utc')

    df.reset_index(inplace=True)
    df.rename(columns={'date':'time'},inplace=True)  

    # get data into required zipline frormat
    df = df[['time','close']]
    
    # SET THE TIME COLUMN AS THE NEW INDEX - AND WRITE IT TO A NEW CSV FILE FOR THE BENCHMARK RETURNS
    df.set_index('time', inplace=True)
    df.to_csv('C:\\zipline_algo\\beta\\data\\daily\\benchmark.csv')
    
    # read back csv column and calculate returns
    dfB = pd.read_csv('/benchmark.csv', index_col=['time'], parse_dates=['time']).tz_localize('utc')
    

    if 'close' not in dfB.columns:
        raise ValueError("The column 'return' not found in the "
                         "benchmark file \n"
                         "Expected benchmark file format :\n"
                         "time, return\n")

    return dfB['close'].sort_index().pct_change().iloc[1:]

#
# --------------------------------------------------------------------------------------------------
# register csv bundle with zipline
# def registerCSVBundle(csvDir, start_session, end_session):
#
#
#
#     register(
#         'custom-csvdir-bundle',
#         csvdir_equities(
#             ['daily'],
#             'C:\\zipline_algo\\beta\\data',
#         ),
#         calendar_name='NYSE', # US equities
#         start_session=start_session,
#         end_session=end_session
#     )
#
#
#     zipline.data.bundles.ingest('custom-csvdir-bundle')
#     zipline.data.bundles.ingestions_for_bundle('custom-csvdir-bundle')
#     zipline.bundles
#     zdb.bundles
#     pass


# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------
# run main

if __name__ == '__main__':

    setPandas()
    setLogging(LOGGING_DIRECTORY, LOG_FILE_NAME, level='INFO')

    startDate, endDate = fnGetStartDate(ticker='SH')
    # endDate = dt.today().date()
    fnDownloadCSVData(['SH','SPY'],start=startDate,end=endDate)

    # get simulation start / end date from config (for zipline bundle registration)
    # start_session = pd.to_datetime(config.get('start_date'), format = '%Y%m%d').tz_localize('UTC')
    # end_session = pd.to_datetime(config.get('end_date'), format = '%Y%m%d').tz_localize('UTC')

    benchmark = fnGetBenchmarkReturns('SPY')


