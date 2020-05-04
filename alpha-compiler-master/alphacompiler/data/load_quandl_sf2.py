
# Code to load raw data from Quandl/SF2
# https://www.quandl.com/databases/SF2/data
# requires the python Quandl package, and the 
# Quandl API key to be set as an ENV variable QUANDL_API_KEY.

import quandl

from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
from alphacompiler.util.sparse_data import pack_sparse_data_for_sf2
from alphacompiler.util import quandl_tools
from logbook import Logger
import datetime
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


def populate_raw_data(tickers, fields, raw_path):
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
            df = quandl.get_table(DS_NAME,
                                  filingdate={'gte': START_DATE, 'lte': END_DATE},
                                  ticker=ticker,
                                  qopts={'columns': ['transactiondate'] + fields})

            #  Change column name to field
            df = df.rename(columns={"transactiondate": "Date"})
            # fill NA transactiondate with filingdate
            df['Date'].fillna(df['filingdate'], inplace=True)
            # df = df.drop(["filingdate"], axis=1)

            # fill NA sharesownedbeforetransaction with 0
            df['sharesownedbeforetransaction'].fillna(0, inplace=True)

            # drop NA transactions
            df = df.loc[~df.transactionshares.isna()]

            # group by transaction data, summing up all other values for the same day
            df = df.groupby(['Date']).agg({'sharesownedbeforetransaction': "sum",
                                                      'transactionshares': "sum",
                                                      'sharesownedfollowingtransaction': "sum",
                                           'filingdate': 'max'}).reset_index()

            # write raw file: raw/
            df = df.rename_axis('None', axis=0)
            df.to_csv(os.path.join(raw_path, "{}.csv".format(sid)))
        except quandl.errors.quandl_error.NotFoundError:
            print("error with ticker: {}".format(ticker))


def all_tickers_for_bundle(fields, bundle_name, raw_path=os.path.join(BASE, RAW_FLDR)):
    tickers = get_ticker_sid_dict_from_bundle(bundle_name)
    populate_raw_data(tickers, fields, raw_path)
    return len(tickers)


if __name__ == '__main__':
    fields = ['sharesownedbeforetransaction', 'transactionshares', 'sharesownedfollowingtransaction', 'filingdate']

    num_tickers = all_tickers_for_bundle(fields, 'quandl')
    pack_sparse_data_for_sf2(num_tickers + 1,  # number of tickers in bundle + 1
                    os.path.join(BASE, RAW_FLDR),
                    fields,
                    os.path.join(BASE, FN))

    print("this worked boss")
