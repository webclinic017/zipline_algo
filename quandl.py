"""
Module for building a complete daily dataset from Quandl's WIKI dataset.
"""
from io import BytesIO
import tarfile
from zipfile import ZipFile

from click import progressbar
from logbook import Logger
import pandas as pd
import requests
from six.moves.urllib.parse import urlencode
from six import iteritems
from trading_calendars import register_calendar_alias

from zipline.utils.deprecate import deprecated
from . import core as bundles
import numpy as np

log = Logger(__name__)

ONE_MEGABYTE = 1024 * 1024
QUANDL_DATA_URL = (
    # 'https://www.quandl.com/api/v3/datatables/WIKI/PRICES.csv?'
    'https://www.quandl.com/api/v3/datatables/SHARADAR/SEP.csv?'
    # 'https://www.quandl.com/api/v3/datatables/SHARADAR/SEP.csv?'
)

QUANDL_DATA_ACTION_URL = (
    # 'https://www.quandl.com/api/v3/datatables/WIKI/PRICES.csv?'
    'https://www.quandl.com/api/v3/datatables/SHARADAR/ACTIONS.csv?'
)

QUANDL_DATA_TICKERS_URL = (
    # 'https://www.quandl.com/api/v3/datatables/WIKI/PRICES.csv?'
    'https://www.quandl.com/api/v3/datatables/SHARADAR/TICKERS.csv?'
)

def format_metadata_url(api_key):
    """ Build the query URL for Quandl WIKI Prices metadata.
    """
    query_params = [('api_key', api_key), ('qopts.export', 'true')]

    return (
        QUANDL_DATA_URL + urlencode(query_params)
    )

def format_metadata_action_url(api_key):
    """ Build the query URL for Quandl WIKI Prices metadata.
    """
    query_params = [('api_key', api_key), ('qopts.export', 'true')]

    return (
        QUANDL_DATA_ACTION_URL + urlencode(query_params)
    )

def format_metadata_tickers_url(api_key):
    query_params = [('api_key', api_key), ('qopts.export', 'true')]

    return (
            QUANDL_DATA_TICKERS_URL + urlencode(query_params)
    )

def load_data_table(file,
                    action_file,
                    tickers_file,
                    index_col,
                    show_progress=False):


    with ZipFile(tickers_file) as zip_file:
        file_names = zip_file.namelist()
        assert len(file_names) == 1, "Expected a single file from Quandl."
        wiki_prices = file_names.pop()
        with zip_file.open(wiki_prices) as table_file:
            with zip_file.open(wiki_prices) as table_file:
                if show_progress:
                    log.info('Parsing raw data.')
                data_table_tickers = pd.read_csv(
                    table_file,
                    # index_col='ticker',
                    usecols=[
                        'ticker',
                        # 'action',
                        'exchange',
                        # 'name',
                        'isdelisted',
                        # 'contraticker',
                        # 'contraname',
                    ],
                )


    """ Load data table from zip file provided by Quandl.
    """
    with ZipFile(action_file) as zip_file:
        file_names = zip_file.namelist()
        assert len(file_names) == 1, "Expected a single file from Quandl."
        wiki_prices = file_names.pop()
        with zip_file.open(wiki_prices) as table_file:
            with zip_file.open(wiki_prices) as table_file:
                if show_progress:
                    log.info('Parsing raw data.')
                data_table_action = pd.read_csv(
                    table_file,
                    parse_dates=['date'],
                    index_col=index_col,
                    usecols=[
                        'date',
                        # 'action',
                        'ticker',
                        # 'name',
                        'value',
                        # 'contraticker',
                        # 'contraname',
                    ],
                )

    with ZipFile(file) as zip_file:
        file_names = zip_file.namelist()
        assert len(file_names) == 1, "Expected a single file from Quandl."
        wiki_prices = file_names.pop()
        with zip_file.open(wiki_prices) as table_file:
            if show_progress:
                log.info('Parsing raw data.')
            data_table = pd.read_csv(
                table_file,
                parse_dates=['date'],
                index_col=index_col,
                usecols=[
                    'ticker',
                    'date',
                    'open',
                    'high',
                    'low',
                    'close',
                    'volume',
                    'dividends',
                    # 'ex-dividend',
                    # 'split_ratio',
                ],
            )
    # data_table_action = data_table_action.set_index(['date', 'ticker'])
    # data_table = data_table.set_index(['date', 'ticker'])
    data_table = pd.merge(data_table, data_table_action, how='left', on=['date', 'ticker'])
    data_table = pd.merge(data_table, data_table_tickers.drop_duplicates(), how='left', on=['ticker'])
    data_table.loc[:, ['value']] = data_table.value.fillna(1)

    # tickers = data_table_tickers.loc[
    #     (data_table_tickers['exchange'] == 'NYSE')]

    # if you want to bring all the symbols please comment below line
    # once you do the change here you will have to deploy this file to your env
    # find env path by "conda env list"
    # C:\ProgramData\Anaconda3\envs\zipline\Lib\site-packages\zipline\data\bundles (example path)
    # data_table = data_table.loc[data_table['ticker'].isin(tickers.index)]
    data_table.rename(
        columns={
            'ticker': 'symbol',
            'dividends': 'ex_dividend',
            'value': 'split_ratio'
        },
        inplace=True,
        copy=False,
    )
    return data_table


def fetch_data_table(api_key,
                     show_progress,
                     retries):
    """ Fetch WIKI Prices data table from Quandl
    """
    for _ in range(retries):
        try:
            if show_progress:
                log.info('Downloading WIKI metadata.')

            metadata = pd.read_csv(
                format_metadata_url(api_key)
            )
            metadata_action = pd.read_csv(
                format_metadata_action_url(api_key)
            )
            metadata_tickers = pd.read_csv(
                format_metadata_tickers_url(api_key)
            )
            # Extract link from metadata and download zip file.
            table_url = metadata.loc[0, 'file.link']
            table_action_url = metadata_action.loc[0, 'file.link']
            table_tickers_url = metadata_tickers.loc[0, 'file.link']
            if show_progress:
                raw_file = download_with_progress(
                    table_url,
                    chunk_size=ONE_MEGABYTE,
                    label="Downloading Sharadar Prices table from Quandl"
                )
                raw_file_action = download_with_progress(
                    table_action_url,
                    chunk_size=ONE_MEGABYTE,
                    label="Downloading Sharadar Prices table from Quandl"
                )
                raw_file_tickers = download_with_progress(
                    table_tickers_url,
                    chunk_size=ONE_MEGABYTE,
                    label="Downloading Sharadar tickers from Quandl"
                )
            else:
                raw_file = download_without_progress(table_url)
                raw_file_action = download_without_progress(table_action_url)
                raw_file_tickers = download_without_progress(table_tickers_url)

            return load_data_table(
                file=raw_file,
                action_file=raw_file_action,
                tickers_file=raw_file_tickers,
                index_col=None,
                show_progress=show_progress,
            )

        except Exception:
            log.exception("Exception raised reading Quandl data. Retrying.")

    else:
        raise ValueError(
            "Failed to download Quandl data after %d attempts." % (retries)
        )


def gen_asset_metadata(data, show_progress):
    if show_progress:
        log.info('Generating asset metadata.')

    data = data.groupby(
        by='symbol'
    ).agg(
        {'date': [np.min, np.max]}
    )
    data.reset_index(inplace=True)
    data['start_date'] = data.date.amin
    data['end_date'] = data.date.amax
    del data['date']
    data.columns = data.columns.get_level_values(0)

    # data['exchange'] = 'QUANDL'
    data['auto_close_date'] = data['end_date'].values + pd.Timedelta(days=1)
    return data


def parse_splits(data, show_progress):
    if show_progress:
        log.info('Parsing split data.')

    data['split_ratio'] = 1.0 / data.split_ratio
    data.rename(
        columns={
            'split_ratio': 'ratio',
            'date': 'effective_date',
        },
        inplace=True,
        copy=False,
    )
    return data


def parse_dividends(data, show_progress):
    if show_progress:
        log.info('Parsing dividend data.')

    data['record_date'] = data['declared_date'] = data['pay_date'] = pd.NaT
    data.rename(
        columns={
            'ex_dividend': 'amount',
            'date': 'ex_date',
        },
        inplace=True,
        copy=False,
    )
    return data


def parse_pricing_and_vol(data,
                          sessions,
                          symbol_map):
    for asset_id, symbol in iteritems(symbol_map):
        asset_data = data.xs(
            symbol,
            level=1
        ).reindex(
            sessions.tz_localize(None)
        ).fillna(0.0)
        yield asset_id, asset_data


@bundles.register('quandl')
def quandl_bundle(environ,
                  asset_db_writer,
                  minute_bar_writer,
                  daily_bar_writer,
                  adjustment_writer,
                  calendar,
                  start_session,
                  end_session,
                  cache,
                  show_progress,
                  output_dir):
    """
    quandl_bundle builds a daily dataset using Quandl's SHARADAR Prices dataset.

    For more information on Quandl's API and how to obtain an API key,
    please visit https://docs.quandl.com/docs#section-authentication
    """
    api_key = environ.get('QUANDL_API_KEY')
    if api_key is None:
        raise ValueError(
            "Please set your QUANDL_API_KEY environment variable and retry."
        )

    raw_data = fetch_data_table(
        api_key,
        show_progress,
        environ.get('QUANDL_DOWNLOAD_ATTEMPTS', 5)
    )
    asset_metadata = gen_asset_metadata(
        raw_data[['symbol', 'date']],
        show_progress
    )
    asset_metadata = pd.merge(asset_metadata, raw_data[['symbol', 'exchange']].drop_duplicates(), how='left', on=['symbol'])
    asset_db_writer.write(asset_metadata)

    # now drop echange and is delisted columns
    del raw_data['exchange']
    del raw_data['isdelisted']

    symbol_map = asset_metadata.symbol
    sessions = calendar.sessions_in_range(start_session, end_session)

    raw_data.set_index(['date', 'symbol'], inplace=True)
    daily_bar_writer.write(
        parse_pricing_and_vol(
            raw_data,
            sessions,
            symbol_map
        ),
        show_progress=show_progress
    )

    raw_data.reset_index(inplace=True)
    raw_data['symbol'] = raw_data['symbol'].astype('category')
    raw_data['sid'] = raw_data.symbol.cat.codes
    adjustment_writer.write(
        splits=parse_splits(
            raw_data[[
                'sid',
                'date',
                'split_ratio',
            ]].loc[raw_data.split_ratio != 1],
            show_progress=show_progress
        ),
        dividends=parse_dividends(
            raw_data[[
                'sid',
                'date',
                'ex_dividend',
            ]].loc[raw_data.ex_dividend != 0],
            show_progress=show_progress
        )
    )


def download_with_progress(url, chunk_size, **progress_kwargs):
    """
    Download streaming data from a URL, printing progress information to the
    terminal.

    Parameters
    ----------
    url : str
        A URL that can be understood by ``requests.get``.
    chunk_size : int
        Number of bytes to read at a time from requests.
    **progress_kwargs
        Forwarded to click.progressbar.

    Returns
    -------
    data : BytesIO
        A BytesIO containing the downloaded data.
    """
    resp = requests.get(url, stream=True)
    resp.raise_for_status()

    total_size = int(resp.headers['content-length'])
    data = BytesIO()
    with progressbar(length=total_size, **progress_kwargs) as pbar:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            data.write(chunk)
            pbar.update(len(chunk))

    data.seek(0)
    return data


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


QUANTOPIAN_QUANDL_URL = (
    'https://s3.amazonaws.com/quantopian-public-zipline-data/quandl'
)


@bundles.register('quantopian-quandl', create_writers=False)
@deprecated(
    'quantopian-quandl has been deprecated and '
    'will be removed in a future release.'
)
def quantopian_quandl_bundle(environ,
                             asset_db_writer,
                             minute_bar_writer,
                             daily_bar_writer,
                             adjustment_writer,
                             calendar,
                             start_session,
                             end_session,
                             cache,
                             show_progress,
                             output_dir):

    if show_progress:
        data = download_with_progress(
            QUANTOPIAN_QUANDL_URL,
            chunk_size=ONE_MEGABYTE,
            label="Downloading Bundle: quantopian-quandl",
        )
    else:
        data = download_without_progress(QUANTOPIAN_QUANDL_URL)

    with tarfile.open('r', fileobj=data) as tar:
        if show_progress:
            log.info("Writing data to %s." % output_dir)
        tar.extractall(output_dir)


register_calendar_alias("QUANDL", "NYSE")
