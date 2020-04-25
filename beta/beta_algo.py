import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pandas as pd
from strategy import Strategy
from zipline.utils.events import date_rules
from zipline.api import (order_target_percent, order_target, schedule_function, symbol)
from utils.log_utils import setup_logging
from beta.beta_config import config
import argparse
import os
import time


logger = setup_logging("beta_algo")


def initialize(context):
    # attach_pipeline(make_pipeline(), 'my_pipeline')
    context.turnover_count = 0

    # etf stock
    context.shorting_on = True
    context.long_stock = symbol('IVV')
    context.short_stock = symbol('SH')

    if context.live_trading is False:
        schedule_function(
            monthly_rebalance,
            date_rule=date_rules.month_start()
        )


def before_trading_start(context, data):
    # context.pipeline_data = pipeline_output('my_pipeline')
    if context.live_trading is True:
        schedule_function(
            monthly_rebalance,
            date_rule=date_rules.month_start()
        )
    context.logic_run_done = False



def after_trading_end(context, data):
    pass


def analyze(context, data):
    pass


def monthly_rebalance(context, data):
    print("-----Monthly Rebalance method Called-------")
    if len(context.portfolio.positions.values()) == 0:
        benchmark_dma = get_dma_returns(context, 200, data.current_dt)
        if benchmark_dma < 0:
            go_inverse(context)
        elif benchmark_dma >= 0:
            go_straight(context)


def rebalance(context, data):
    print("-----Rebalance method Called-------")
    benchmark_dma = get_dma_returns(context, 200, data.current_dt)
    if benchmark_dma < 0 and not context.shorting_on:
        go_inverse(context)
    elif benchmark_dma >= 0 and context.shorting_on:
        go_straight(context)


def go_inverse(context):
    context.shorting_on = True
    order_target_percent(context.long_stock, 0)
    order_target_percent(context.short_stock, 1)


def go_straight(context):
    context.shorting_on = False
    order_target_percent(context.short_stock, 0)
    order_target_percent(context.long_stock, 1)


def handle_data(context, data):
    try:
        if context.logic_run_done is False:
            rebalance(context, data)
            context.logic_run_done = True
        stop_loss_check(context, data)
    except ValueError as e:
        print(e)


def stop_loss_check(context, data):
    if context.live_trading is True:
        for symbol, position in context.portfolio.positions.items():
            data.current(symbol, 'price')
        time.sleep(60)

    positions = list(context.portfolio.positions.values())
    position_list = []

    for position in positions:
        position_list.append(position.asset)
        if not position.amount > 0:
            continue
        if position.last_sale_price == 0:
            last_price = data.history(position.asset, 'close', 1, '1d')[0]
        else:
            last_price = position.last_sale_price

        prev_price = data.history(position.asset, 'close', 2, '1d')[0]
        if last_price <= 0 or prev_price <= 0:
            raise ValueError("Prices not available")
        daily_gain_loss = float("{0:.2f}".format((last_price - prev_price) * 100 / prev_price))
        net_gain_loss = float("{0:.2f}".format((last_price - position.cost_basis) * 100 / position.cost_basis))

        if net_gain_loss < -3 or daily_gain_loss < -3:
            order_target(position.asset, 0)
            strategy.SendMessage('Stop loss Sell Order', 'Sell all shares of {}'.format(str(position.asset.symbol)))
            try:
                print("Stop loss triggered for: {} on {}".format(position.asset.symbol,
                                                                 data.current_dt.strftime('%d/%m/%Y')))
            except Exception as e:
                print(e)

    print("Daily handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def get_dma_returns(context, period, dma_end_date):
    returns = context.trading_environment.benchmark_returns[:dma_end_date]
    if returns.size > period:
        returns = 1 + returns[-period:]
    else:
        return 0
    dma_return = 100 * (returns.prod() - 1)
    return dma_return


if __name__ == '__main__':
    start_date = pd.to_datetime(config.get('start_date'), format='%Y%m%d').tz_localize('UTC')
    end_date = pd.to_datetime(config.get('end_date'), format='%Y%m%d').tz_localize('UTC')

    parser = argparse.ArgumentParser(description='live mode.')
    parser.add_argument('--live_mode', help='True for live mode')
    args = parser.parse_args()

    kwargs = {'start': start_date,
              'end': end_date,
              'initialize': initialize,
              'handle_data': handle_data,
              'analyze': analyze,
              'before_trading_start': before_trading_start,
              'after_trading_end': after_trading_end,
              'bundle': 'quandl',
              'capital_base': config.get('capital_base'),
              'algo_name': config.get('name'),
              'algo_id': config.get('id'),
              'benchmark_symbol': config.get('benchmark_symbol')}

    if args.live_mode == 'True':
        if os.path.exists('test.state'):
            os.remove('test.state')
        print("Running in live mode.")
        kwargs['tws_uri'] = 'localhost:7497:1232'
        kwargs['live_trading'] = True
    else:
        kwargs['live_trading'] = False

    strategy = Strategy(kwargs)
    strategy.run_algorithm()

    if args.live_mode != 'True':
        input("Press any key to exit")
