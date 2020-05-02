# ------------------------------------------------------------
# fnInsiderTrading.py
#
#
# This script is designed to hold  trading criteria functions
# ------------------------------------------------------------
# created by joe loss

import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
import pandas as pd
import numpy as np
from datetime import datetime as dt
import pytz
from long_term_low_risk.ltlr_config import config
import pandas_datareader as pdd
import statsmodels.api as sm
from statsmodels import regression
import math



# --------------------------------------------------------------------------------------------------
# adjust pandas settings

def setPandas():
    import warnings
    warnings.simplefilter('ignore', category=FutureWarning)

    options = {
        'display': {
            'max_columns': None,
            'max_colwidth': 800,
            'colheader_justify': 'center',
            'max_rows': 20,
            # 'min_rows': 10,
            'precision': 2,
            'float_format': '{:,.2f}'.format,
            # 'max_seq_items': 50,         # Max length of printed sequence
            'expand_frame_repr': False,  # Don't wrap to multiple pages
            # 'show_dimensions': False
        },
        'mode': {
            'chained_assignment': None   # Controls SettingWithCopyWarning
        }
    }
    for category, option in options.items():
        for op, value in option.items():
            pd.set_option('%s.%s' % (category, op), value)  # Python 3.6+



# ------------------------------------------------------------
# get SPY returns manually

def fnGetSpyReturns():

    # Using config start/end date:
    start_date = pd.to_datetime(config.get('start_date'), format='%Y%m%d') - pd.to_timedelta(365, unit='d')
    end_date = pd.to_datetime(config.get('end_date'), format='%Y%m%d')

    panel_data = pdd.DataReader('SPY', 'yahoo', start_date, end_date)

    # localize timezones
    panel_data.tz_localize(pytz.utc)

    # calculate returns
    rSPY = panel_data['Adj Close'].pct_change()[1:]

    # convert SPY index to UTC
    rSPY.index = rSPY.index.to_datetime().tz_localize('UTC')
    rSPY = pd.DataFrame(rSPY)

    return rSPY


# ------------------------------------------------------------
# data pre-processing for insider trading data

def fnProcessInsiderTrades(dfIT):

    cols = ['ticker', 'filingdate',
            # 'ownername', 'officertitle',
            # 'isdirector', 'isofficer', 'istenpercentowner',
            # 'securitytitle', 'directorindirect',
            'transactiondate', 'sharesownedbeforetransaction',
            'transactionshares', 'sharesownedfollowingtransaction']

    dfIT = dfIT[cols]

    # fill NA values with filing date
    dfIT['transactiondate'].fillna(dfIT['filingdate'], inplace=True)

    # fill NA sharesownedbeforetransaction with 0
    dfIT['sharesownedbeforetransaction'].fillna(0, inplace=True)

    # drop NA transactions
    dfIT = dfIT.loc[~dfIT.transactionshares.isna()]

    # calculate pct of shares bot/sld
    dfIT['pctSharesBotSld'] = ((dfIT['sharesownedfollowingtransaction'] - dfIT['sharesownedbeforetransaction']) / dfIT['sharesownedbeforetransaction']) * 100

    # if no shares before transaction, remove from data (infinite number because of div 0. Not good data!)
    dfIT['pctSharesBotSld'].replace(np.inf, np.nan, inplace=True)
    dfIT.dropna(inplace=True)

    dfIT.reset_index(drop=True, inplace=True)

    # convert transaction date to datetime and localize timezone
    dfIT['transactiondate'] = pd.to_datetime(dfIT['transactiondate']).dt.tz_localize(pytz.utc)

    # check NAs
    if dfIT.transactiondate.isna().nunique() > 1:
        print("----- WARNING: NA VALUES IN TRANSACTION DATE -----")
    else:
        pass

    return dfIT


# ------------------------------------------------------------
# search insider trades >= Bot/Sld amount

def fnFilterInsiderTransactions(dfIT, pctTraded = 10.0, side = 'B', tPeriod=7, tUnit='d'):

    # timeDelta (filter on dates)
    tDelta = pd.to_timedelta(tPeriod, unit=tUnit)

    # groupby date, ticker DESC
    df = dfIT.groupby(['transactiondate','ticker']).sum()
    df.sort_index(level=0, ascending=False, inplace=True, sort_remaining=True)

    # choose bought, sold, or either
    if side == 'B':
        df = df.loc[df['pctSharesBotSld'] >= pctTraded]
    elif side == 'S':
        df = df.loc[df['pctSharesBotSld'] <= pctTraded]
    else:
        df = df.loc[df['pctSharesBotSld'] >= abs(pctTraded)]

    # get first ticker
    # df.index.levels[1][1]
    # get last ticker
    # df.index.levels[1][-1]

    # set time range using most recent transaction date - timeDelta
    tRange = df.index.levels[0][-1] - tDelta
    df.reset_index(inplace=True)

    # filtered df (dfStock)
    dfS = df.loc[df['transactiondate'] >= tRange]
    # print('\n Insider Trades filtered on criteria: \n', dfS)

    # return stock tickers
    tickers = dfS['ticker'].values.tolist()
    # print("\n Tickers to buy: \n", tickers)

    return tickers


# ------------------------------------------------------------
# linear regression to compute historical alpha/beta

def linreg(x, y):

    # We add a constant so that we can also fit an intercept (alpha) to the model
    x = sm.add_constant(x)
    model = regression.linear_model.OLS(y, x).fit()

    # Remove the constant now that we're done
    x = x[:, 1]
    return model.params[0], model.params[1]


# ----------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------
# run

if __name__ == '__main__':

    setPandas()
    dfRaw = pd.read_csv('C:\\Users\\DEVELOPMENT1\\Downloads\\SHARADAR-SF2.csv')

    dfIT = fnProcessInsiderTrades(dfRaw)

    tickers = fnFilterInsiderTransactions(dfIT, pctTraded=10.0, side='B', tPeriod=7, tUnit='d')

