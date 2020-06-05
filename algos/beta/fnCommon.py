# --------------------------------------------------------------------------------------------------
# created by joe.loss
#
#
# --------------------------------------------------------------------------------------------------
import os, sys
from datetime import datetime as dt
import pandas as pd
import numpy as np
# import pyodbc as pyodbc
import logging
from importlib import reload

#
#
# def setPandas():
#     import warnings
#     warnings.simplefilter('ignore', category=FutureWarning)
#
#     options = {
#         'display': {
#             'max_columns': None,
#             'max_colwidth': 800,
#             'colheader_justify': 'center',
#             'max_rows': 30,
#             # 'min_rows': 10,
#             'precision': 2,
#             'float_format': '{:,.2f}'.format
#             # 'max_seq_items': 50,         # Max length of printed sequence
#             'expand_frame_repr': True,  # Don't wrap to multiple pages
#             # 'show_dimensions': False
#         },
#         'mode': {
#             'chained_assignment': None   # Controls SettingWithCopyWarning
#         }
#     }
#     for category, option in options.items():
#         for op, value in option.items():
#             pd.set_option(f"{category}.{op}', value)  # Python 3.6+


# --------------------------------------------------------------------------------------------------
# set up logging

def setLogging(LOGGING_DIRECTORY = os.path.join('D:\\', 'logs', 'srAdvisors.v2', dt.today().strftime('%Y-%m-%d'), 'python'), LOG_FILE_NAME = os.path.basename(__file__) + '.log', level = 'INFO'):

    # reloads logging (useful for iPython only)
    reload(logging)

    # init logging
    handlers = [logging.StreamHandler(sys.stdout)]

    if not os.path.exists(LOGGING_DIRECTORY):
        os.makedirs(LOGGING_DIRECTORY)
    handlers.append(logging.FileHandler(os.path.join(LOGGING_DIRECTORY, LOG_FILE_NAME), 'a'))

    # noinspection PyArgumentList
    logging.basicConfig(level = level,
                        format = '%(asctime)s - %(levelname)s - %(message)s',
                        datefmt = '%m/%d/%Y %I:%M:%S %p',
                        handlers = handlers)


# --------------------------------------------------------------------------------------------------
# set up output filepath

def setOutputFile(OUTPUT_DIRECTORY = os.path.join('D:\\', 'tmp', 'advisorscodebase'), file = 'file'):

    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)

    path = os.path.join(OUTPUT_DIRECTORY, file)
    return path


# --------------------------------------------------------------------------------------------------
# download csv data

import pandas as pd
import pytz
from datetime import datetime as dt
import pandas_datareader as pdr
from collections import OrderedDict

data = OrderedDict()

curDate = dt.today()
startDate = pd.to_datetime('2015-11-30')

def fnDownloadPriceData(startDate='2015-11-30',endDate=curDate):
    # indices=['AAPL','MSFT',]
    indices=['SPY',]
    # indices=['^SP500TR','^PUT','^RUTTR','^BXM','^FVX','^TNX','^TYX']
    startDate = pd.to_datetime(startDate,format='%Y-%m-%d')- pd.to_timedelta(365,unit='d')
    endDate = pd.to_datetime(curDate,format='%Y%m%d')
    for idx in indices:
        data[idx] = pdr.DataReader('{}'.format(idx),'yahoo',startDate,endDate)
        data[idx] = data[idx][['Open','High','Low','Close','Volume','Adj Close']]
        data[idx].index=pd.DatetimeIndex(data[idx].index)
        data[idx].index = data[idx].index.tz_localize(pytz.utc)
        data[idx].rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume','Adj Close':'adj close'},inplace=True)
        # data[idx]['pctReturn']= data[idx]['Adj Close'].pct_change()[1:]
        data[idx].to_csv('{}.csv'.format(idx))

    return

fnDownloadPriceData(startDate,curDate)

