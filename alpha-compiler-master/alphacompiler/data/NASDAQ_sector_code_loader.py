
"""
Downloads sector codes from NASDAQ.  For exchanges: NASDAQ, NYSE, AMEX

Created by Peter Harrington (pbharrin) on 10/21/17.
The download also provides industries within sectors.
"""
import numpy as np
import pandas as pd
import sys
from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
import os
import requests
from pathlib import Path
from zipfile import ZipFile
from six.moves.urllib.parse import urlencode

# this gets all the data for the three exchanges 6000+ tickers
BASE_URL = "http://www.nasdaq.com/screening/companies-by-industry.aspx?&render=download"

BASE_PATH = str(Path.home())
RAW_FILE = "NASDAQ_table.csv"
SID_FILE = "NASDAQ_sids.npy"  # persisted np.array where
SID_FILE_IPO = "NASDAQ_sids_IPO.npy"
from io import BytesIO

# NASDAQ sectors, not the same as Morningstar
SECTOR_CODING = {"Industrials": 0,
           "Basic Materials": 1,
           "Consumer Cyclical": 2,
           "Consumer Defensive": 3,
           "Real Estate": 4,
           "Energy": 5,
           "Financial Services": 6,
           "Healthcare": 7,
           "Communication Services": 8,
           "Utilities": 9,
           "Technology": 10,
           "": -1}

QUANDL_DATA_TICKERS_URL = (
    # 'https://www.quandl.com/api/v3/datatables/WIKI/PRICES.csv?'
    'https://www.quandl.com/api/v3/datatables/SHARADAR/TICKERS.csv?'
)

def format_metadata_tickers_url(api_key):
    query_params = [('api_key', api_key), ('qopts.export', 'true')]

    return (
            QUANDL_DATA_TICKERS_URL + urlencode(query_params)
    )

def download_without_progress(url):
    """
    Download data from a URL, returning a BytesIO containing the loaded data.

    Parameters
    ----------
    url : str
        A URL that can be understood by ``requests.get``.

    Returns
    -------
    data : BytesIO
        A BytesIO containing the downloaded data.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    return BytesIO(resp.content)

def create_sid_table_from_file(ticker_df):
    """reads the raw file, maps tickers -> SIDS,
    then maps sector strings to integers, and saves
    to the file: SID_FILE"""
    df = ticker_df
    df = df.drop_duplicates()

    coded_sectors_for_ticker = df["sector"].map(SECTOR_CODING)
    coded_sectors_for_ticker.fillna(-1, inplace=True)
    ae_d = get_ticker_sid_dict_from_bundle('quandl')
    N = max(ae_d.values()) + 1

    # create empty 1-D array to hold data where index = SID
    sectors = np.full(N, -1, np.dtype('int64'))

    # iterate over Assets in the bundle, and fill in sectors
    for ticker, sid in ae_d.items():
        try:
            sectors[sid] = coded_sectors_for_ticker.get(ticker, -1)
        except Exception as e:
            print(e)

    np.save(os.path.join(BASE_PATH , SID_FILE), sectors)


def create_sid_table_from_file_ipo(ticker_df):
    """reads the raw file, maps tickers -> SIDS,
    then maps sector strings to integers, and saves
    to the file: SID_FILE"""
    df = ticker_df
    df = df.drop_duplicates()

    # coded_sectors_for_ticker = df["Sector"].map(SECTOR_CODING)

    ae_d = get_ticker_sid_dict_from_bundle('quandl')
    N = max(ae_d.values()) + 1

    # create empty 1-D array to hold data where index = SID
    ipoyears = np.full(N, -1, np.dtype('int64'))

    # iterate over Assets in the bundle, and fill in sectors
    for ticker, sid in ae_d.items():
        try:
            ipoyears[sid] = int(df.loc[ticker].firstpricedate[:4])
        except Exception as e:
            print(e)

    np.save(os.path.join(BASE_PATH , SID_FILE_IPO), ipoyears)


if __name__ == '__main__':
    INPUT_FILE = os.path.join(BASE_PATH , RAW_FILE)
    # r = requests.get(BASE_URL, allow_redirects=True)
    # open(INPUT_FILE, 'wb').write(r.content)
    metadata_tickers = pd.read_csv(
        format_metadata_tickers_url('PPzVtduYsyxVgf9z1WGo')
    )
    table_tickers_url = metadata_tickers.loc[0, 'file.link']
    raw_file_tickers = download_without_progress(table_tickers_url)

    with ZipFile(raw_file_tickers) as zip_file:
        file_names = zip_file.namelist()
        assert len(file_names) == 1, "Expected a single file from Quandl."
        wiki_prices = file_names.pop()
        with zip_file.open(wiki_prices) as table_file:
            with zip_file.open(wiki_prices) as table_file:
                data_table_tickers = pd.read_csv(
                    table_file,
                    index_col='ticker',
                    usecols=[
                        'ticker',
                        # 'action',
                        'sector',
                        'firstpricedate',
                    ],
                )

    create_sid_table_from_file(data_table_tickers)
    create_sid_table_from_file_ipo(data_table_tickers)
    print("all done boss")