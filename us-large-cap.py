from zipline.api import order, record, symbol
from zipline.errors import SymbolNotFound
import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes
from zipline.pipeline import Pipeline
from zipline.api import (
    attach_pipeline,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
)

current_year = None
def initialize(context):
    # context.additional_data = pd.DataFrame.from_csv('test2.csv', index_col=['ticker'])
    # context.securities = []
    attach_pipeline(make_pipeline(), 'my_pipeline')

def make_pipeline():
    fd = Fundamentals()
    sectors = NASDAQSectorCodes()

    return Pipeline(
        columns={
            # 'longs': rsi.top(3),
            # 'shorts': rsi.bottom(3),
            'marketcap': fd.marketcap,
            'liabilities': fd.liabilities,
            'revenue': fd.revenue,
            'rnd': fd.rnd,
            'netinc': fd.netinc,
            'pe': fd.pe,
            #'CAPEX': fd.CAPEX_MRQ,
            'ipoyear': sectors,
        },
    )


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def get_large_cap_symbols(context, year_end_date):
    return context.additional_data.query("calendardate == '{}' and marketcap >  10000000000".format(year_end_date))

def handle_data(context, data):
    pipeline_data = context.pipeline_data

    # remove assests with no market cap
    interested_assets = pipeline_data.dropna(subset=['marketcap'])

    # filter assets based on
    # 1. market cap is > 10000000000
    # 2. liabilities < 180000000000
    # 3. should have invested more than or equal 6% of total revenue in RND
    # 4. net income should be positive
    # 5. pe should be between 15 and 60
    # 6. ipo should be earlier than at least two years
    interested_assets = interested_assets.query("marketcap > 10000000000 and liabilities < 180000000000 and ((100 * rnd)/revenue) >= 6"
                                                "and netinc > 0 and (15 <= pe <= 60) and (ipoyear < {} or ipoyear == -1)".format(data.current_dt.year - 2))

    print(interested_assets.head())


if __name__ == '__main__':
    start_date = '20111130'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    end_date = '20121231'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data, before_trading_start=before_trading_start
                            , bundle='quandl', capital_base=100000)

    print(results)