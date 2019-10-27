
# Code to load raw data from Quandl/SF1
# https://www.quandl.com/data/SF1-Core-US-Fundamentals-Data/
# requires the python Quandl package, and the 
# Quandl API key to be set as an ENV variable QUANDL_API_KEY.

import quandl

from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
from alphacompiler.util.sparse_data import pack_sparse_data
from alphacompiler.util import quandl_tools
from logbook import Logger
import datetime
from os import listdir
import os
from pathlib import Path
import shutil

BASE = str(Path.home())
DS_NAME = 'SHARADAR/SF1'   # quandl DataSet code
RAW_FLDR = "raw"  # folder to store the raw text file
VAL_COL_NAME = "Value"
START_DATE = '1999-01-01'
END_DATE = datetime.datetime.today().strftime('%Y-%m-%d')

if not os.path.exists(os.path.join(BASE, RAW_FLDR)):
    os.makedirs(os.path.join(BASE, RAW_FLDR))
else:
    shutil.rmtree(os.path.join(BASE, RAW_FLDR))
    # os.rmdir(os.path.join(BASE, RAW_FLDR))
    os.makedirs(os.path.join(BASE, RAW_FLDR))

FN = "SF1.npy"

log = Logger('load_quandl_sf1.py')


def populate_raw_data(tickers, fields, raw_path):
    """tickers is a dict with the ticker string as the key and the SID
    as the value.  """
    quandl_tools.set_api_key()

    # existing = listdir(RAW_FLDR)

    for ticker, sid in tickers.items():
        # if "%d.csv" % sid in existing:
        #     continue
        try:
            query_str = "%s %s" % (DS_NAME, ticker)
            print("fetching data for: {}".format(query_str))

            # df = quandl.get_table(query_str, start_date=START_DATE, end_date=END_DATE)
            df = quandl.get_table(DS_NAME,
                                  calendardate={'gte': START_DATE, 'lte': END_DATE},
                                  ticker=ticker,
                                  qopts={'columns': ['dimension', 'datekey'] + fields})

            df = df[df.dimension == "ARQ"]  # only use As-Reported numbers

            #  Change column name to field
            df = df.rename(columns={"datekey": "Date"})
            df = df.drop(["dimension"], axis=1)

            # write raw file: raw/
            df.to_csv(os.path.join(raw_path,"{}.csv".format(sid)))
        except quandl.errors.quandl_error.NotFoundError:
            print("error with ticker: {}".format(ticker))


def all_tickers_for_bundle(fields, bundle_name, raw_path=os.path.join(BASE,RAW_FLDR)):
    tickers = get_ticker_sid_dict_from_bundle(bundle_name)
    populate_raw_data(tickers, fields, raw_path)
    return len(tickers)


if __name__ == '__main__':

    # fields = ['accoci', 'assets', 'assetsavg',
    #  'assetsc', 'assetsnc', 'assetturnover', 'bvps', 'capex', 'cashneq', 'cashnequsd', 'cor', 'consolinc',
    #  'currentratio', 'de', 'debt', 'debtc', 'debtnc', 'debtusd', 'deferredrev', 'depamor', 'deposits', 'divyield',
    #  'dps', 'ebit', 'ebitda', 'ebitdamargin', 'ebitdausd', 'ebitusd', 'ebt', 'eps', 'epsdil', 'epsusd', 'equity',
    #  'equityavg', 'equityusd', 'ev', 'evebit', 'evebitda', 'fcf', 'fcfps', 'fxusd', 'gp', 'grossmargin', 'intangibles',
    #  'intexp', 'invcap', 'invcapavg', 'inventory', 'investments', 'investmentsc', 'investmentsnc', 'liabilities',
    #  'liabilitiesc', 'liabilitiesnc', 'marketcap', 'ncf', 'ncfbus', 'ncfcommon', 'ncfdebt', 'ncfdiv', 'ncff', 'ncfi',
    #  'ncfinv', 'ncfo', 'ncfx', 'netinc', 'netinccmn', 'netinccmnusd', 'netincdis', 'netincnci', 'netmargin', 'opex',
    #  'opinc', 'payables', 'payoutratio', 'pb', 'pe', 'pe1', 'ppnenet', 'prefdivis', 'price', 'ps', 'ps1', 'receivables',
    #  'retearn', 'revenue', 'revenueusd', 'rnd', 'roa', 'roe', 'roic', 'ros', 'sbcomp', 'sgna', 'sharefactor',
    #  'sharesbas', 'shareswa', 'shareswadil', 'sps', 'tangibles', 'taxassets', 'taxexp', 'taxliabilities', 'tbvps',
    #  'workingcapital']

    fields = ['assets', 'capex', 'cor', 'currentratio', 'de', 'debt', 'divyield', 'ebit', 'ebitda', 'ebt', 'eps', 'fcf',
              'grossmargin', 'inventory', 'investments', 'liabilities', 'marketcap', 'ncf', 'netinc', 'netmargin',
              'opex', 'payables', 'payoutratio', 'pb', 'pe', 'receivables', 'revenue', 'rnd', 'roa', 'roe', 'sgna',
              'taxassets', 'taxliabilities', 'workingcapital']

    num_tickers = all_tickers_for_bundle(fields, 'quandl')
    pack_sparse_data(num_tickers + 1,  # number of tickers in buldle + 1
                    os.path.join(BASE, RAW_FLDR),
                    fields,
                    os.path.join(BASE,FN))

    print("this worked boss")
