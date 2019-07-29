import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pandas as pd
from zipline.api import order_target, symbol
from strategy import Strategy
import argparse


def initialize(context):
    pass


def handle_data(context, data):
    stock = symbol('AAPL')
    order_target(stock, 200)


def analyze(context, data):
    pass


def before_trading_start(context, data):
    pass


if __name__ == '__main__':
    print("starting strategy")
    parser = argparse.ArgumentParser(description='live mode.')

    parser.add_argument('--live_mode', help='True for live mode')

    args = parser.parse_args()
    print(args)

    # start date for the backtest in yyyymmdd format string
    start_date = '20150101'
    # converting date string to date
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    # end date for the backtest in yyyymmdd format string
    end_date = '20190331'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    kwargs = {'start': start_date,
              'end': end_date,
              'initialize': initialize,
              'handle_data': handle_data,
              'analyze': analyze,
              'before_trading_start': before_trading_start,
              'bundle': 'quandl',
              'capital_base': 100000,
              'algo_name': 'mid_term_low_risk',
              'benchmark_symbol': 'SPY',
              }

    if args.live_mode == 'True':
        print("Running in live mode.")
        kwargs['tws_uri'] = 'localhost:7497:1232'
        kwargs['live_trading'] = True

    strategy = Strategy(kwargs)
    strategy.run_algorithm()
