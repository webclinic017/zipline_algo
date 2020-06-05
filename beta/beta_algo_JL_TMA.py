# zipline run --bundle custom-csvdir-bundle -s 2007-08-01 -e 2020-05-01 -f C:\Users\jloss\PyCharmProjects\zipline_algo\beta\beta_algo_JL.py

# --------------------------------------------------------------------------------------------------
# Module Imports

# todo: interactive brokers tick data
# todo: write function to download, process, and register custom-csvdir-bundle
# todo: ask Denis for other strategy logic (going short, etc)

# todo: csv headers:
# todo:  date	  open	  high	   low	  close	  volume    dividend	split
# todo: 8/1/2007  124.36  125.46  122.88  123.26   264550   	0	        1



import inspect
import logging
import os
import sys
import warnings
import argparse
from functools import reduce
from datetime import datetime as dt
import pandas as pd
import zipline.finance.cancel_policy
from talib import SMA, EMA
from zipline.api import *
from zipline.utils.events import date_rules, time_rules
from zipline.finance.cancel_policy import EODCancel

import matplotlib.pyplot as plt
from matplotlib import style

from modified_beta_strategy import Strategy

style.use('fivethirtyeight')

from beta.beta_config import config
from fnCommon import setLogging
from fnTradingCritera import setPandas
from datetime import timedelta
import operator
from functools import partial
warnings.simplefilter(action='ignore',category = UserWarning)

# quandl_api_key='PPzVtduYsyxVgf9z1WGo'


# todo:
# Ending Cash
# plot MAs and trades
# look at SH borrow rate
# download and use minute data for SPY / SH


# --------------------------------------------------------------------------------------------------
# setup logging

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

LOGGING_DIRECTORY = os.path.join('C:\\', 'Users\\jloss\\PyCharmProjects\\zipline_algo\\beta\\', 'logs\\', dt.today().strftime('%Y-%m-%d'))

LOG_FILE_NAME = os.path.basename(__file__) + '.log'


# --------------------------------------------------------------------------------------------------
# todo:
# liquidate long when shortest MA crosses below intermediate MA or if close < entryPrice - 3000/bigPointValue
# if ((shortSMA < medSMA) | () )
# if context.longSpread
# if context.longSpread:
# if (shortSMA < medSMA) or (SPY)
# liguitate short when shortest MA crosses above intermediate MA or if close > entryPrice + 3000/bigPointValue


# --------------------------------------------------------------------------------------------------
# init

def initialize(context):

    set_benchmark(symbol("SPY"))

    set_cancel_policy(EODCancel())
    # set_max_order_count(1)

    # set_max_leverage(1.0)

    context.longSpread = False
    context.shortSpread = False

    context.longStock = symbol('SH')
    context.shortStock = symbol('SPY')
    #
    # schedule_function(fnTripleMovingAverageCrossover,
    #                   date_rules.every_day(),
    #                   time_rules.market_open(minutes = 20))

    schedule_function(handle_data,
                      date_rules.every_day(),
                      # time_rules.market_close(minutes = 45))
                      time_rules.market_open(minutes = 45))

    # schedule_function(fnLiquidatePositions,
    #                   date_rules.every_day())
    #                   time_rules.market_open(minutes = 1))

    schedule_function(recordVars,
                      date_rules.every_day())


# --------------------------------------------------------------------------------------------------
# handle data

def handle_data(context, data):

    SH = context.longStock
    SPY = context.shortStock

    pos = context.portfolio.positions

    openOrders = get_open_orders()

    tPeriod = data.history(SPY, 'close', 310, '1d')

    # try EMA as well
    context.shortSMA = SMA(tPeriod.values, timeperiod = 49)     # 49
    context.medSMA = SMA(tPeriod.values, timeperiod = 194)      # 99
    context.longSMA = SMA(tPeriod.values, timeperiod = 309)     # 149

    shortSMA = round(context.shortSMA[-1], 2)
    medSMA = round(context.medSMA[-1], 2)
    longSMA = round(context.longSMA[-1], 2)

    currentPosition = context.portfolio.positions

    try:
        if len(currentPosition) > 0:

            # bigPointValue = pointValue x priceScale (default = 50 for SPY)
            bigPointValue = 50.0  # 250

            # if (context.longSpread or context.shortSpread):
            if context.longSpread:
                lastClose = data.current(SPY, 'close')

                entryPrice = context.portfolio.positions[1].cost_basis
                bpv =  3000 / bigPointValue

                # pos=context.metrics_tracker.positions
                # entryPrice = pos[1].inner_position.cost_basis


                if (shortSMA < medSMA) | (lastClose < (entryPrice - bpv)):
                    logging.info('----- CLOSING LONG POSITION -----')
                    order_target_percent(SH, 0.0)

                    context.longSpread = False
                    # context.shortSpread = False

            elif context.shortSpread:
                lastClose = data.current(SPY, 'close')
                entryPrice = context.portfolio.positions[0].cost_basis
                bpv =  3000/ bigPointValue

                # pos=context.metrics_tracker.positions
                # entryPrice = pos[0].inner_position.cost_basis

                if (shortSMA > medSMA) | (lastClose > (entryPrice + bpv)):
                    logging.info('----- CLOSING SHORT POSITION -----')
                    order_target_percent(SPY, 0.0)

                    context.shortSpread = False
                    # context.longSpread = False

        else:
            fnTripleMovingAverageCrossover(context, data)


    except Exception as e:
        logging.error(str(e))


# --------------------------------------------------------------------------------------------------
# TMA strategy

def fnTripleMovingAverageCrossover(context, data):

    SH = context.longStock
    SPY = context.shortStock

    pos = context.portfolio.positions


    tPeriod = data.history(SPY, 'close', 310, '1d')

    # try EMA as well
    context.shortSMA = SMA(tPeriod.values, timeperiod = 49)     # 49
    context.medSMA = SMA(tPeriod.values, timeperiod = 194)      # 99
    context.longSMA = SMA(tPeriod.values, timeperiod = 309)     # 149

    shortSMA = round(context.shortSMA[-1], 2)
    medSMA = round(context.medSMA[-1], 2)
    longSMA = round(context.longSMA[-1], 2)


    # short & intermediate each must be greater > long
    if (shortSMA > longSMA) & (medSMA > longSMA):
        logging.info('ma49: %s and ma194: %s are higher than ma309: %s' % (shortSMA, medSMA, longSMA))
        logging.info('\tlooking to enter long position...')

        # Buy when shortest MA crosses above intermed
        if (shortSMA > medSMA) & (context.longSpread == False):
            logging.info('ma49: %s crossed above ma194: %s' % (shortSMA, medSMA))
            logging.info('----- LONG ORDER PLACED -----')

            order_target_percent(SH, -1.5)
            # order_target_percent(SPY, 0.0)

            openOrders = get_open_orders()

            if len(openOrders) > 0:
                logging.info('waiting to fill order...')

            # newOrders = context.blotter.new_orders[0]
            # logging.info("Ticker: %s, nShares: %s" % (newOrders.sid, newOrders.amount))
            # update if order is filled

            # while not context.portfolio.positions:
            #     logging.info('waiting for position update...')
            #     continue

            # elif len(context.portfolio.positions) > 0:
            # else:
            context.longSpread = True
            context.shortSpread = False


    # short + intermediate < Long
    elif (shortSMA < longSMA) & (medSMA < longSMA):
        logging.info("ma49: %s and ma194: %s are lower than ma309: %s" % (shortSMA, medSMA, longSMA))

        logging.info('\tlooking to enter short position....')

        # sell when shortest MA crosses below intermediate MA
        if (shortSMA < medSMA) & (context.shortSpread==False):
            logging.info('ma49: %s crossed below ma194: %s' %(shortSMA, medSMA))
            logging.info('----- SHORT ORDER PLACED -----')

            order_target_percent(SPY, -1.0)
            # order_target_percent(SH, 0.0)


            openOrders = get_open_orders()

            if len(openOrders) > 0:
                logging.info('waiting to fill order...')


            # elif len(context.portfolio.positions) > 0:
            # else:
            context.shortSpread = True
            context.longSpread = False

            # newOrders = context.blotter.new_orders[0]
            # logging.info("Ticker: %s, nShares: %s" % (newOrders.sid, newOrders.amount))

            # todo:
            # order placement SAME DAY as signal

            # if context.portfolio.positions:

            # if not context.blotter.open_orders:

    else:
        pass

            # record(pos)

        # if context.longSpread | context.shortSpread:
        #     fnLiquidatePositions(context,data)



# --------------------------------------------------------------------------------------------------
# record variables

def recordVars(context, data):
    SH = context.longStock
    SPY = context.shortStock

    shortSMA = context.shortSMA[-1]
    medSMA = context.medSMA[-1]
    longSMA = context.longSMA[-1]

    pos = context.metrics_tracker.positions
    port = context.metrics_tracker.portfolio
    pnl = context.metrics_tracker.portfolio.pnl
    returns = context.metrics_tracker.portfolio.returns

    # context.metrics_tracker.portfolio.current_portfolio_weights
    # context.metrics_tracker.portfolio.positions_exposure

    record(shortSMA = shortSMA,
           medSMA = medSMA,
           longSMA = longSMA,
           SPY = data.current(SPY, 'close'),
           SH = data.current(SH, 'close'),
           posMetrics = pos,
           portMetrics = port,
           pnlMetrics = pnl,
           pnlRtn = returns,
           # positions = context.portfolio.positions,
           # portval = context.portfolio.portfolio_value,
           # pnl = context.portfolio.pnl,
           # rtn = context.portfolio.returns,
           )

    # print(shortSMA[-1], medSMA[-1], longSMA[-1], SPY, SH, context.portfolio.pnl, context.portfolio.positions)


# --------------------------------------------------------------------------------------------------
# analyze

def analyze(context, perf):

    fig = plt.figure()
    ax = fig.add_subplot(111)

    # ax2 = fig.add_subplot(111)

    ax.plot(perf.portfolio_value,
            # c='b',
            label='portfolio_value',
            linewidth=2.5)

    # ax.plot(perf.ending_cash,
            # c='r',
            # label='ending_cash',
            # linewidth=1.0)

    # perf.portfolio_value.plot(ax=ax)
    # perf.ending_cash.plot(ax=ax2)
    # ax1.set_ylabel('portfolio $ value')
    # ax2.set_ylabel('ending cash')

    plt.legend(loc=0, fontsize='small')

    plt.show()



# --------------------------------------------------------------------------------------------------
#
# def fnLiquidatePositions(context, data):
    # SPY = context.longStock
    # SH = context.shortStock
    #
    # shortSMA = context.shortSMA[-1]
    # medSMA = context.medSMA[-1]
    # longSMA = context.longSMA[-1]
    #
    # # bigPointValue = pointValue x priceScale (default = 50 for SPY)
    # bigPointValue = 50.0  # 250
    #
    # # if (context.longSpread or context.shortSpread):
    # if context.longSpread:
    #     lastClose = data.current(SPY,'close')
    #     entryPrice = context.portfolio.positions[1].cost_basis
    #     bpv =  3000 / bigPointValue
    #
    #     # pos=context.metrics_tracker.positions
    #     # entryPrice = pos[1].inner_position.cost_basis
    #
    #
    #     if (shortSMA < medSMA) | (lastClose < (entryPrice-bpv)):
    #         logging.info('----- CLOSING LONG POSITION -----')
    #         order_target_percent(SH, 0.0)
    #
    #         context.longSpread = False
    #         # context.shortSpread = False
    #
    # if context.shortSpread:
    #     lastClose = data.current(SPY,'close')
    #     entryPrice = context.portfolio.positions[0].cost_basis
    #     bpv =  3000/250
    #
    #     # pos=context.metrics_tracker.positions
    #     # entryPrice = pos[0].inner_position.cost_basis
    #
    #     if (shortSMA > medSMA) | (lastClose > (entryPrice+bpv)):
    #         logging.info('----- CLOSING SHORT POSITION -----')
    #         order_target_percent(SPY, 0.0)
    #
    #         context.shortSpread = False
    #         # context.longSpread = False





# def stop_loss_check(context, data):
#     for symbol, position in context.portfolio.positions.items():
#         data.current(symbol, 'price')
#     time.sleep(60)
#
#     positions = list(context.portfolio.positions.values())
#     position_list = []
#
#     for position in positions:
#         position_list.append(position.asset)
#         if not position.amount > 0:
#             continue
#         if position.last_sale_price == 0:
#             last_price = data.history(position.asset, 'close', 1, '1d')[0]
#         else:
#             last_price = position.last_sale_price
#
#         prev_price = data.history(position.asset, 'close', 2, '1d')[0]
#         if last_price <= 0 or prev_price <= 0:
#             raise ValueError("Prices not available")
#         daily_gain_loss = float("{0:.2f}".format((last_price - prev_price) * 100 / prev_price))
#         net_gain_loss = float("{0:.2f}".format((last_price - position.cost_basis) * 100 / position.cost_basis))
#
#         if net_gain_loss < -3 or daily_gain_loss < -3:
#             order_target(position.asset, 0)
#             try:
#                 print("Stop loss triggered for: {} on {}".format(position.asset.symbol,
#                                                                  data.current_dt.strftime('%d/%m/%Y')))
#             except Exception as e:
#                 print(e)
#
#     print("Daily handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------
# run main

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
              # 'before_trading_start': before_trading_start,
              # 'after_trading_end': after_trading_end,
              'bundle': 'custom-csvdir-bundle',
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




# # --------------------------------------------------------------------------------------------------
# # end program
#
#     logging.info("========== END PROGRAM ==========")
#     logging.info('\nEnding portfolio statistics:\n%s' % perf.loc[perf.index[-1]])
#     logging.info('\nLarge negative returns:\n%s' % perf.loc[perf.returns <- .10]['returns'])
#
#
#     except Exception as e:
#         logging.error(str(e), exc_info = True)
#
# # CLOSE LOGGING
# for handler in logging.root.handlers:
#     handler.close()
#
# logging.shutdown()
