import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pandas as pd
from strategy import Strategy
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
import datetime
from zipline.utils.events import date_rules
from zipline.api import (attach_pipeline, order_target_percent, order_target, pipeline_output, schedule_function)
from utils.log_utils import setup_logging
from mid_term_high_risk.mthr_config import config
import argparse
import pickle
import time


# stop loss non addition limit set to 15 days
stop_loss_prevention_days = 25
# max exposure per sector set to 15%
max_sector_exposure = 0.15

logger = setup_logging("mid_term_high_risk")


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.stop_loss_list = pd.Series()
    context.count = 0

    context.sector_wise_exposure = dict()
    context.sector_stocks = {}
    context.turnover_count = 0


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')
    if context.live_trading is False:
        schedule_function(
            rebalance,
            date_rule=date_rules.week_start()
        )
    else:
        try:
            with open('stop_loss_list.pickle', 'rb') as handle:
                context.stop_loss_list = pickle.load(handle)
        except:
            context.stop_loss_list = pd.Series()


def after_trading_end(context, data):
    if context.live_trading is True:
        with open('stop_loss_list.pickle', 'wb') as handle:
            pickle.dump(context.stop_loss_list, handle, protocol=pickle.HIGHEST_PROTOCOL)


def analyze(context, data):
    pass


def make_pipeline():
    fd = Fundamentals()
    sectors = NASDAQSectorCodes()
    ipos = NASDAQIPO()

    return Pipeline(
        columns={
            'marketcap': fd.marketcap,
            'liabilities': fd.liabilities,
            'revenue': fd.revenue,
            'eps': fd.eps,
            'rnd': fd.rnd,
            'netinc': fd.netinc,
            'pe': fd.pe,
            'ipoyear': ipos,
            'yoy_sales': fd.yoy_sales,
            'qoq_earnings': fd.qoq_earnings,
            'sector': sectors
        },
    )


def recalc_sector_wise_exposure(context, data):
    # loop thru all the positions
    net = context.portfolio.portfolio_value
    for sector, stocks in context.sector_stocks.items():
        sector_exposure = 0
        for stock in stocks:
            position = context.portfolio.positions.get(stock)
            if position is not None:
                if position.last_sale_price == 0:
                    last_price = data.history(position.asset, 'close', 1, '1d')[0]
                else:
                    last_price = position.last_sale_price
                exposure = (last_price * position.amount) / net
                sector_exposure += exposure
        context.sector_wise_exposure[sector] = sector_exposure


def rebalance(context, data):
    print("-----Rebalance method Called-------")
    positions = list(context.portfolio.positions.values())
    cash = context.portfolio.cash
    stop_list = context.stop_loss_list
    pipeline_data = context.pipeline_data

    recalc_sector_wise_exposure(context, data)

    benchmark_dma = get_dma_returns(context, 70, data.current_dt)
    if benchmark_dma < 0:
        return

    # remove assests with no market cap
    interested_assets = pipeline_data.dropna(subset=['marketcap'])

    # filter assets based on
    # 1. market cap is small cap (300million to 2billion)
    # 2. liabilities < 180bn
    # 3. yoy sales > 20%
    # 4. ipo should be earlier than at least two years
    # 5 sort by qoq_earnings
    interested_assets = interested_assets.query("marketcap < 2000000000 "
                                                "and marketcap > 300000000"
                                                "and liabilities < 180000000000 "
                                                "and (yoy_sales >= 0.2 or yoy_sales != yoy_sales)"
                                                "and (ipoyear < {} or ipoyear == -1)"
                                                "and pe < 300"
                                                .format(data.current_dt.year - 2))

    interested_assets = interested_assets.sort_values(by=['qoq_earnings'], ascending=False)

    net = context.portfolio.portfolio_value
    for position in context.portfolio.positions.values():
        if position.last_sale_price == 0:
            last_price = data.history(position.asset, 'close', 1, '1d')[0]
        else:
            last_price = position.last_sale_price
        exposure = (last_price * position.amount) / net
        # selling half to book profit
        if exposure > 0.15:
            order_target_percent(position.asset, exposure / 2)
            strategy.SendMessage('Book Profit Sell Order', 'Book Profit by selling half of '+str(position.asset.symbol))
            context.turnover_count += 1
            print("Half profit booking done for {}".format(position.asset.symbol))

    position_list = []
    for position in positions:
        position_list.append(position.asset)

    # Buy logic
    if len(position_list) < 25:
        for stock in interested_assets.index.values:
            # only buy if not part of positions already
            # if stock not in position_list and stock not in stop_list and stock.exchange in ('NASDAQ', 'NYSE'):
            if stock not in position_list and stock not in stop_list:
                # avg_vol = data.history(stock, 'volume', 50, '1d').mean()
                # if avg_vol < 10000:
                #     continue

                avg_vol = data.history(stock, 'volume', 50, '1d')[:-1].mean()
                min_vol = data.history(stock, 'volume', 50, '1d')[:-1].min()
                price = data.history(stock, 'price', 1, '1d').item()
                if (price * min_vol) < 11000 or avg_vol < 10000:
                    continue

                sector = interested_assets.loc[stock].sector
                quantity = get_quantity(context.portfolio.portfolio_value,
                                        context.sector_wise_exposure, sector, price, cash)

                if quantity > 0 and data.can_trade(stock):
                    order_target(stock, quantity)
                    strategy.SendMessage('Buy Order', 'Buy {} shares of {}'.format(str(quantity), str(stock.symbol)))
                    context.turnover_count += 1
                    cash -= quantity * data.current(stock, 'price')
                    if context.sector_stocks.get(sector, None) is None:
                        context.sector_stocks.update({sector: [stock]})
                    else:
                        context.sector_stocks[sector].append(stock)
                    print("Buy order triggered for: {} on {} for {} shares"
                          .format(stock.symbol, data.current_dt.strftime('%d/%m/%Y'), quantity))
                position_list.append(stock)
                # limit the max position to 25 at all stages
                if len(position_list) >= 25:
                    break


def handle_data(context, data):
    for symbol, position in context.portfolio.positions.items():
        data.current(symbol, 'price')
    time.sleep(60)
    positions = list(context.portfolio.positions.values())
    stop_list = context.stop_loss_list

    # update stop loss list
    for i1, s1 in stop_list.items():
        stop_list = stop_list.drop(index=[i1])
        s1 -= 1
        if s1 > 0:
            stop_list = stop_list.append(pd.Series([s1], index=[i1]))

    benchmark_dma = get_dma_returns(context, 70, data.current_dt)
    if benchmark_dma < 0:
        sell_all(positions, context)
        return

    # Sell logic
    position_list = []
    for position in positions:
        position_list.append(position.asset)
        # sell at stop loss
        if not position.amount > 0:
            continue
        if position.last_sale_price == 0:
            last_price = data.history(position.asset, 'close', 1, '1d')[0]
        else:
            last_price = position.last_sale_price
        net_gain_loss = float("{0:.2f}".format((last_price - position.cost_basis)*100/position.cost_basis))
        if net_gain_loss < -3:
            order_target(position.asset, 0)
            strategy.SendMessage('Sell Order', 'Buy all shares of {}'.format(str(position.asset.symbol)))
            context.turnover_count += 1
            try:
                context.sector_stocks[context.pipeline_data.loc[position.asset].sector].remove(position.asset)

                print("Stop loss triggered for: "+position.asset.symbol)
                # add to stop loss list to prevent re-buy
                stop_loss = pd.Series([stop_loss_prevention_days], index=[position.asset])
                stop_list = stop_list.append(stop_loss)
            except Exception as e:
                context.count += 1
                print(str(context.count) + " : " + str(e) + " : " + str(position.asset.symbol))

    context.stop_loss_list = stop_list
    print("Daily handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def get_quantity(portfolio_value, sector_wise_exposure, sector, price, cash):
    available_exposure = cash / portfolio_value
    if sector in sector_wise_exposure:
        sector_exposure = sector_wise_exposure.get(sector)
        if sector_exposure < max_sector_exposure:
            exposure = min(max_sector_exposure - sector_exposure, 0.05, available_exposure)
            exposure = round(exposure, 4)
            sector_wise_exposure[sector] += exposure
        else:
            exposure = 0
    else:
        exposure = min(0.05, available_exposure)
        sector_wise_exposure[sector] = exposure
    quantity = int((exposure * portfolio_value) / price)
    return quantity


def sell_all(positions, context):
    print("Sell All rule triggered for "+str(len(positions)))
    for position in positions:
        order_target_percent(position.asset, 0)
        strategy.SendMessage('Sell All and Exit Market', 'Sell all shares of {}'.format(str(position.asset.symbol)))
        context.turnover_count += 1


def get_dma_returns(context, period, dma_end_date):
    dma_start_date = dma_end_date - datetime.timedelta(days=period)
    returns = 1 + context.trading_environment.benchmark_returns.loc[dma_start_date: dma_end_date]
    if returns.size < 50:
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
              'algo_name': 'mid_term_high_risk',
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

    input("Press any key to exit")
