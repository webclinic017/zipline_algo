
# Code to load raw data from Quandl/SF2
# https://www.quandl.com/databases/SF2/data
# requires the python Quandl package, and the 
# Quandl API key to be set as an ENV variable QUANDL_API_KEY.

import quandl
from long_term_low_risk.fnTradingCritera import setPandas
from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
from alphacompiler.util.sparse_data import pack_sparse_data_for_sf2
from alphacompiler.util import quandl_tools
from logbook import Logger
import datetime
import numpy as np
import pandas as pd
import pytz
from os import listdir
import os
from pathlib import Path
import shutil
import time

BASE = str(Path.home())
DS_NAME = 'SHARADAR/SF2'   # quandl DataSet code
RAW_FLDR = "raw2"  # folder to store the raw text file
START_DATE = '1999-01-01'
END_DATE = datetime.datetime.today().strftime('%Y-%m-%d')

if not os.path.exists(os.path.join(BASE, RAW_FLDR)):
    os.makedirs(os.path.join(BASE, RAW_FLDR))
else:
    shutil.rmtree(os.path.join(BASE, RAW_FLDR))
    # os.rmdir(os.path.join(BASE, RAW_FLDR))
    os.makedirs(os.path.join(BASE, RAW_FLDR))

FN = "SF2.npy"

log = Logger('load_quandl_sf2.py')


# ------------------------------------------------------------
# data pre-processing for insider trading data
def fnProcessInsiderTrades(df, nDaysDiff):
    # drop NA transaction dates
    df = df[df.transactiondate.notnull()]
    df = df[df.transactionshares.notnull()]
    df['transactionshares'].dropna(inplace=True)
    # drop transactions with < 1 transaction share (otherwise pct bot/sld is something like 0.03%)
    df = df.loc[abs(df['transactionshares']) > 1]

    # df = df.loc[~df.transactionshares.isna()]
    # fill NA sharesownedbeforetransaction with 0
    # df['sharesownedbeforetransaction'].fillna(0, inplace=True)

    # calculate pct of shares bot/sld
    df['pctSharesBotSld'] = ((df['sharesownedfollowingtransaction'] - df['sharesownedbeforetransaction']) / df[
        'sharesownedbeforetransaction']) * 100

    # if no shares before transaction, remove from data (infinite number because of div 0. Not good data!)
    df['pctSharesBotSld'].replace(np.inf, np.nan, inplace=True)
    df.dropna(inplace=True)

    df.reset_index(drop=True, inplace=True)

    # convert transaction date to datetime and localize timezone
    df['transactiondate'] = pd.to_datetime(df['transactiondate'])

    # check NAs
    if df.transactiondate.isna().nunique() > 1:
        print("----- WARNING: NA VALUES IN TRANSACTION DATE -----")
    elif df.transactionshares.isna().nunique() > 1:
        print("----- WARNING: NA VALUES IN TRANSACTION SHARES -----")
    else:
        pass

    # calculate difference in number of days (filingDate - transactiondate)
    df['transactiondate'] = pd.to_datetime(df['transactiondate']).dt.tz_localize(pytz.utc)
    df['filingdate'] = pd.to_datetime(df['filingdate']).dt.tz_localize(pytz.utc)

    df['dDiff'] = (df['filingdate'] - df['transactiondate'])
    df['dDiffInt'] = df['dDiff'].dt.days
    df['dDiffInt'] = df['dDiffInt'].astype(float)

    # filter out difference in days by nDaysDiff
    df = df[abs(df['dDiffInt']) <= nDaysDiff]

    # finally, groupby filingdate and sum
    # df = df.groupby(['ticker', 'filingdate']).sum()

    return df


def populate_raw_data(tickers, input_fields, output_fields, raw_path):
    """tickers is a dict with the ticker string as the key and the SID
    as the value.  """
    quandl_tools.set_api_key()

    # existing = listdir(RAW_FLDR)

    for ticker, sid in tickers.items():
        # if "%d.csv" % sid in existing:
        #     continue
        try:
            time.sleep(0.1)
            query_str = "%s %s" % (DS_NAME, ticker)
            print("fetching data for: {}".format(query_str))

            # df = quandl.get_table(query_str, start_date=START_DATE, end_date=END_DATE)

            rawData = quandl.get_table(DS_NAME,
                                       filingdate={'gte': START_DATE, 'lte': END_DATE},
                                       ticker=ticker,
                                       qopts={'columns': input_fields},
                                       paginate=True)

            df = fnProcessInsiderTrades(rawData, nDaysDiff=3)

            #  Group by and Change column name to field
            if not df.empty:
                df = df.groupby('filingdate').sum().reset_index()
            df = df.rename(columns={"filingdate": "Date"})

            df = df[output_fields]

            # write raw file: raw/
            df = df.rename_axis('None', axis=0)
            df.to_csv(os.path.join(raw_path, "{}.csv".format(sid)))
        except quandl.errors.quandl_error.NotFoundError:
            print("error with ticker: {}".format(ticker))


def all_tickers_for_bundle(input_fields, output_fields, bundle_name, raw_path=os.path.join(BASE, RAW_FLDR)):
    tickers = get_ticker_sid_dict_from_bundle(bundle_name)
    populate_raw_data(tickers, input_fields, output_fields, raw_path)
    return len(tickers)


if __name__ == '__main__':

    # set custom pandas settings
    setPandas()

    # import full csv of data (2020-05-06) for debug purposes
    # rawData = pd.read_csv('C:\\Users\\DEVELOPMENT1\\rawSF2\\SHARADAR_SF2.csv')

    # process and clean insider transactions data, then filter on (filingdate - transactiondate) nDays <=3
    # df = fnProcessInsiderTrades(rawData, nDaysDiff=3)

    # ---------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------
    # QUANDL LOAD:
    input_fields = ['filingdate', 'transactiondate', 'sharesownedbeforetransaction', 'transactionshares',
                    'sharesownedfollowingtransaction']
    output_fields = ['Date', 'sharesownedbeforetransaction', 'transactionshares',
                     'sharesownedfollowingtransaction', 'pctSharesBotSld', 'dDiffInt']

    num_tickers = all_tickers_for_bundle(input_fields, output_fields, 'quandl')
    pack_sparse_data_for_sf2(num_tickers + 1,  # number of tickers in bundle + 1
                    os.path.join(BASE, RAW_FLDR),
                    output_fields,
                    os.path.join(BASE, FN))

    print("this worked boss")
