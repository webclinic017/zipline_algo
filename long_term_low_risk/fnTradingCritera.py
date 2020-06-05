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
            'expand_frame_repr': True,  # Don't wrap to multiple pages
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
# commbines all insider trading csv into one dataframe

def fnCombineInsiderTrades(directoryPath):
    import glob

    glued_data = pd.DataFrame()

    for file_name in glob.glob(directoryPath + '*.csv'):
        x = pd.read_csv(file_name, low_memory=False)
        glued_data = pd.concat([glued_data, x], axis=0)

    return glued_data



# ------------------------------------------------------------
# data pre-processing for insider trading data

def fnProcessInsiderTrades(df, nDaysDiff):

    cols = ['ticker', 'filingdate',
            'transactiondate', 'sharesownedbeforetransaction',
            'transactionshares', 'sharesownedfollowingtransaction']

    df = df[cols]

    # drop NA transaction dates
    df['transactiondate'].dropna(inplace=True)

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
    df['dDiffInt']= float(df['dDiffInt'])

    # filter out difference in days by nDaysDiff
    df = df[abs(df['dDiffInt']) <= nDaysDiff]

    # finally, groupby filingdate and sum
    # df = df.groupby(['ticker', 'filingdate']).sum()

    return df


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
        df = df.loc[df['pctSharesBotSld'] <= -pctTraded]
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



    # ----------------------------------------------------------------------------------
    # analyze insider transaction data

    # directory for the raw insider transaction data files
    directoryPath = 'C:\\Users\\DEVELOPMENT1\\raw2\\'

    dfRaw = fnCombineInsiderTrades(directoryPath)


    dfRaw['transactiondate'] = pd.to_datetime(dfRaw['transactiondate'])
    dfRaw['filingdate'] = pd.to_datetime(dfRaw['filingdate'])
    dfRaw['dDiff'] = (dfRaw['filingdate'] - dfRaw['transactiondate'])
    dfRaw['dDiffInt'] = dfRaw['dDiff'].dt.days
    tmp = dfRaw.loc[dfRaw['dDiffInt'] >=10]
    print(tmp[['transactiondate', 'filingdate', 'dDiff']])





    dfRaw = pd.read_csv('C:\\Users\\DEVELOPMENT1\\Downloads\\SHARADAR-SF2.csv')

    # dfIT = fnProcessInsiderTrades(dfRaw)

    # tickers = fnFilterInsiderTransactions(dfIT, pctTraded=10.0, side='B', tPeriod=7, tUnit='d')

