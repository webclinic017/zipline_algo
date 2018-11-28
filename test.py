"""
A simple Pipeline algorithm that longs the top 3 stocks by RSI and shorts
the bottom 3 each day.
"""
from zipline.utils.run_algo import run_algorithm
import pandas as pd
from six import viewkeys
from zipline.api import (
    attach_pipeline,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
)
from zipline.pipeline import Pipeline

from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes
from zipline.pipeline.factors import RSI

ONE_THIRD = 1.0 / 3.0

def make_pipeline():
    rsi = RSI()
    fd = Fundamentals()
    # sectors = NASDAQSectorCodes()

    return Pipeline(
        columns={
            'longs': rsi.top(3),
            'shorts': rsi.bottom(3),
            'ROE': fd.marketcap,
            #'CAPEX': fd.CAPEX_MRQ,
            # 'sector': sectors,
        },
    )


def handle_data(context, data):
    print (data.current_dt)

    # Pipeline data will be a dataframe with boolean columns named 'longs' and
    # 'shorts'.
    pipeline_data = context.pipeline_data
    print (pipeline_data.head())
    all_assets = pipeline_data.index

    longs = all_assets[pipeline_data.longs]
    shorts = all_assets[pipeline_data.shorts]

    record(universe_size=len(all_assets))

    # Build a 2x-leveraged, equal-weight, long-short portfolio.
    for asset in longs:
        order_target_percent(asset, ONE_THIRD)

    for asset in shorts:
        order_target_percent(asset, -ONE_THIRD)

    # Remove any assets that should no longer be in our portfolio.
    portfolio_assets = longs | shorts
    positions = context.portfolio.positions
    for asset in viewkeys(positions) - set(portfolio_assets):
        # This will fail if the asset was removed from our portfolio because it
        # was delisted.
        if data.can_trade(asset):
            order_target_percent(asset, 0)


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')

    # Rebalance each day.  In daily mode, this is equivalent to putting
    # `rebalance` in our handle_data, but in minute mode, it's equivalent to
    # running at the start of the day each day.

def before_trading_start(context, data):
    # schedule_function(rebalance, date_rules.every_day())
    context.pipeline_data = pipeline_output('my_pipeline')

if __name__ == '__main__':
    start_date = '20110131'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    end_date = '20121231'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data, before_trading_start=before_trading_start
                            , bundle='quandl', capital_base=100000)

    print(results)