from zipline.api import symbol
from strategy import Strategy
import pandas as pd
import argparse
from algos.virtual_broker_sample_ltlr_algo.vb_sample_config import config
from utils.algo_utils import get_run_mode
import utils.api_connector as api_conn

data = None


def initialize(context):
    pass


def handle_data(context, data):
    update_all_prices()
    place_pending_orders()


def analyze(context, data):
    pass


def before_trading_start(context, data):
    stock = symbol('AAPL')
    # price = data.current(stock, 'price')
    price = api_conn.get_price(stock.sid)
    print("Aapl price is {}".format(price))


def after_trading_end(context, data):
    pass


def place_pending_orders():
    # pick pending orders from the db and place them
    pass


def update_all_prices():
    # Fetch all stocks from db and update their prices
    pass


if __name__ == '__main__':
    print("starting strategy")
    start_date = pd.Timestamp.today()
    end_date = pd.Timestamp.today()

    parser = argparse.ArgumentParser(description='live mode.')
    parser.add_argument('--live_mode', help='True for live mode', default='backtest')
    args = parser.parse_args()

    kwargs = {'start': start_date, 'end': end_date, 'initialize': initialize, 'handle_data': handle_data,
              'analyze': analyze, 'before_trading_start': before_trading_start, 'after_trading_end': after_trading_end,
              'bundle': 'quandl', 'capital_base': config.get('capital_base'), 'algo_name': config.get('name'),
              'algo_id': config.get('id'), 'benchmark_symbol': config.get('benchmark_symbol'),
              'tws_uri': get_run_mode(args.live_mode)[0], 'live_trading': get_run_mode(args.live_mode)[1]}

    strategy = Strategy(kwargs)
    strategy.run_algorithm()
