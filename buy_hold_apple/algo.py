import pandas as pd
from zipline.api import order_target, symbol
from strategy import Strategy


def initialize(context):
    pass


def handle_data(context, data):
    stock = symbol('AAPL')
    stock1 = symbol('GOOG')
    order_target(stock, 100)
    order_target(stock1, 100)
    if context.datetime.date().strftime("%Y%m%d") == "20150114":
        order_target(stock, 0)
    if context.datetime.date().strftime("%Y%m%d") == "20150120":
        order_target(stock1, 0)

def analyze(context, data):
    pass


def before_trading_start(context, data):
    pass


if __name__ == '__main__':
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
              'benchmark_symbol': 'SPY'}

    strategy = Strategy(kwargs)
    strategy.run_algorithm()
