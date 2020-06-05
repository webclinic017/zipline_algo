import quandl, zipline
import pandas as pd
import pytz
from datetime import datetime as dt
from alphacompiler.util import quandl_tools, zipline_data_tools
from long_term_low_risk.fnTradingCritera import setPandas
from beta.beta_config import config
import logging



# df = pd.DataFrame(quandl.get_table('SHARADAR/SFP', ticker=['SH','SPY']))


def fnDownloadData(startDate, endDate, lastUpdated=True):

    df = pd.DataFrame(quandl.get_table('SHARADAR/SFP', date={'gte':startDate,'lte':endDate}, ticker=['SH','SPY'], paginate=True))

    return df





def fnProcessData(df):

    df.drop(columns='lastupdated',inplace=True)

    df['split_ratio'] = 1.0

    # df.rename(columns={'dividends':'ex_dividend','close':'adjusted_close', 'closeunadj':'unadjusted_close', 'open':'adjusted_open','high':'adjusted_high','low':'adjusted_low'},inplace=True)
    df.rename(columns={'dividends':'dividend','closeunadj':'unadjusted_close', },inplace=True)

    df['unadjusted_open'] = df['open']
    df['unadjusted_low'] = df['low']
    df['unadjusted_high'] = df['high']

    df['split_ratio'].loc[(df.date=='2016-06-23') & (df.ticker=='SH')] = 2.0
    split_ratio = df.loc[(df.date=='2016-06-23') & (df.ticker=='SH')]['split_ratio']


    df['unadjusted_open'].loc[df.ticker=='SH'] = df['open'] / 2.0
    df['unadjusted_low'].loc[df.ticker=='SH'] = df['low'] / 2.0
    df['unadjusted_high'].loc[df.ticker=='SH'] = df['high'] / 2.0

    # df['unadjusted_close'].loc[(df.date<='2016-06-23') & (df.ticker=='SH')] =


    df['unad']

# get last updated
# quandl.get_table('SHARADAR/SFP', lastupdated={'gte':'2017-11-03'},  ticker=['SH','SPY'],)

# get more than 10,000 rows of data
# quandl.get_table('SHARADAR/SFP', date={'gte':startDate,'lte':endDate}, ticker=['SH','SPY'], paginate=True)

# get specific date range
# quandl.get_table('SHARADAR/SFP', date={'gte':'2017-01-01', 'lte':'2017-10-30'}, ticker=['SH','SPY'], paginate=True)






if __name__ == '__main__':

    # custom pandas settings
    setPandas()
    # set quandl API key
    quandl_tools.set_api_key()

    startDate = pd.to_datetime(config.get('start_date'), format='%Y%m%d').tz_localize(pytz.utc)
    endDate = pd.to_datetime(config.get('end_date'), format='%Y%m%d').tz_localize(pytz.utc)

    # bulk data download
    df = fnDownloadData(startDate=startDate, endDate=endDate)

    # df.head()


