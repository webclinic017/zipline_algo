import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import pandas as pd
from strategy import Strategy
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
from zipline.utils.events import date_rules
import numpy as np
from zipline.api import (attach_pipeline, order_target_percent, order_target, pipeline_output, schedule_function)
from utils.log_utils import setup_logging
from mid_term_low_risk.mtlr_config import config
import argparse


"""
    Every time a stock is removed because of breaching the stop loss limit, it is added to a stop_loss_list along with 
    the stop_loss_prevention_days. Every trading day, the number of days for the stock is reduced until it reaches 0, 
    on which, it is removed from the stop_loss_list, after which it can be bought again
    
    The algo skips all the stocks present in the stop loss list, for stop_loss_prevention_days days
"""
# stop loss non addition limit set to 15 days
stop_loss_prevention_days = 15

"""
    The maximum amount of exposure allowed per sector is configured using max_sector_exposure. All the stocks are 
    divided into 11 sectors and -1 for info not available. This limit ensures that a new stocks is not added to the 
    portfolio if the current exposure for that sector exceeds max_sector_exposure * 100 %
    
    The sector exposure is updated each day to ensure the exposure change due to price changes is taken into account
"""
# max exposure per sector set to 15%
max_sector_exposure = 0.21
initial_exposure = 0.07
dma = 200

logger = setup_logging("mid_term_low_risk")


def initialize(context):
    """
    :param context: global variable used through the backtest for carrying forwarding the parameter values to next day
    The initialize method is called only once, at the start of the backtest. It initializes all the parameters required
    for running the backtest
    :return: None
    """
    # attach_pipeline, attaches the data pipeline from quandl/quantopian
    attach_pipeline(make_pipeline(), 'my_pipeline')

    # initializing variables  as part of the context variable, so that it can be easily accessed through the backtest
    # stop_loss_list: A list of recently removed stocks because of stop loss, stocks part of this list are not bought
    context.stop_loss_list = pd.Series()
    # sector_wise_exposure: dictionary of how much exposure each sector has in the portfolio, it is updated daily
    context.sector_wise_exposure = dict()
    # sector_stocks: dictionary of which stocks are present as part of which sector, it is update on buy/sell orders
    context.sector_stocks = {}
    context.turnover_count = 0

    # scheduling the rebalance function to be called at start of each week
    schedule_function(
        rebalance,
        date_rule=date_rules.week_start()
    )


def analyze(context, data):
    pass


def make_pipeline():
    """
    Function to define the data pipeline (coming from quandl)
    :return: None
    """
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


def recalc_sector_wise_exposure(context):
    """
    The function is used to update the portfolio exposure for each sector
    :param context: global variable used through the backtest for carrying forwarding the parameter values to next day
    :return: None, updated values of sector_wise_exposure
    """
    # loop thru all the positions
    net = context.portfolio.portfolio_value
    for sector, stocks in context.sector_stocks.items():
        sector_exposure = 0
        for stock in stocks:
            position = context.portfolio.positions.get(stock)
            if position is not None:
                exposure = (position.last_sale_price * position.amount) / net
                sector_exposure += exposure
        context.sector_wise_exposure[sector] = sector_exposure


def before_trading_start(context, data):
    """
    This function is called every trading day before the start of trading. Any calculations or actions that needs to be
    done before starting the trading happens in before_trading_start function
    :param context: global variable used through the backtest for carrying forwarding the parameter values to next day
    :param data: mandatory to call as part of scheduled function, unused in our case
    :return: None, updated value for pipeline data for the day
    """
    context.pipeline_data = pipeline_output('my_pipeline')


def rebalance(context, data):
    """
    The function used to rebalance and book profits in a stock. The net exposure of any particular stock goes beyond
    15% of the net portfolio, half of the stock is sold thereby booking partial profit in it and
    reducing the exposure to 7.5%
    :param context: global variable used through the backtest for carrying forwarding the parameter values to next day
    :param data: mandatory to call as part of scheduled function, unused in our case
    :return: None
    """
    # get the list of current positions and store it in the local variable called positions
    positions = list(context.portfolio.positions.values())

    # get the pipeline data and store it in the local variable called pipeline_data
    pipeline_data = context.pipeline_data

    # get the current cash value and store it in the local variable called cash
    cash = context.portfolio.cash

    # get the stop list and store it in the local variable called stop_list
    stop_list = context.stop_loss_list

    # call the recalc function to update the exposure to all sectors
    recalc_sector_wise_exposure(context)

    benchmark_dma = get_dma_returns(context, dma, data.current_dt)
    if benchmark_dma < 0:
        return

    # remove assests with no market cap
    interested_assets = pipeline_data.dropna(subset=['marketcap'])

    # filter assets based on
    # 1. market cap is large cap (>10billion)
    # 2. liabilities < 180bn
    # 3. yoy sales > 3% or none
    # 4. ipo should be earlier than at least two years or n/a
    # 5. should have invested more than or equal 6% of total revenue in RND
    # 6. net income should be positive
    # 7. should not have a decrease in earnings
    interested_assets = interested_assets.query("marketcap > 10000000000 "
                                                "and liabilities < 180000000000 "
                                                "and (yoy_sales >= 0.03 or yoy_sales != yoy_sales)"
                                                "and (ipoyear < {} or ipoyear == -1)"
                                                "and ((100 * rnd) / revenue) >= 6"
                                                "and netinc > 0"
                                                "and qoq_earnings > 0"
                                                .format(data.current_dt.year - 2))

    # sort the buy candidate stocks based on their quarterly earnings
    interested_assets = interested_assets.replace([np.inf, -np.inf], np.nan)
    interested_assets = interested_assets.dropna(subset=['qoq_earnings'])
    interested_assets = interested_assets.sort_values(by=['qoq_earnings'], ascending=False)

    net = context.portfolio.portfolio_value
    for position in context.portfolio.positions.values():
        exposure = (position.last_sale_price * position.amount) / net
        # selling half to book profit
        if exposure > 0.15:
            # order_target_percent is a zipline function that allows to place orders based on the percentage target
            # that needs to be achieved. so order_target(xyz, 0.05) = will put a buy/sell order for xyx stock to reach
            # an equivalent of 5% of the current portfolio value.
            order_target_percent(position.asset, exposure / 2)
            strategy.SendMessage('Book Profit Sell Order', 'Book Profit by selling half of '+str(position.asset.symbol))
            context.turnover_count += 1
            print("Half profit booking done for {}".format(position.asset.symbol))

    # initialize an empty list of positions, used during the buy logic
    position_list = []
    for position in positions:
        position_list.append(position.asset)

    # Buy logic
    # Limit the total number of stocks in the portfolio to 25
    # If there are already 25 stock in the portfolio do not go into buy logic
    if len(position_list) < 25:
        # Loop through all the stocks shortlisted in the interested_assets
        for stock in interested_assets.index.values:
            # only buy if not part of positions already
            # if stock not in position_list and stock not in stop_list and stock.exchange in ('NASDAQ', 'NYSE'):
            if stock not in position_list and stock not in stop_list:

                # Calculate 50day average volume for the stock
                avg_vol = data.history(stock, 'volume', 50, '1d').mean()
                # Only buy if the 50day average volume for the stock is above 10,000 to prevent low traded stocks to
                # enter our portfolio
                # if avg_vol < 10000:
                #     continue

                avg_vol = data.history(stock, 'volume', 50, '1d').mean()
                min_vol = data.history(stock, 'volume', 50, '1d').min()
                price = data.history(stock, 'price', 1, '1d').item()
                if (price * min_vol) < 10000 or (price * avg_vol) < 20000:
                    continue

                # get yesterday's closing price of the stock
                price = data.history(stock, 'price', 1, '1d').item()
                # get the sector of the stock
                sector = interested_assets.loc[stock].sector
                # get the quantity of stock that should be bought based on our exposure criteria
                quantity = get_quantity(context.portfolio.portfolio_value,
                                        context.sector_wise_exposure, sector, price, cash)

                if quantity > 0 and data.can_trade(stock):
                    order_target(stock, quantity)
                    strategy.SendMessage('Buy Order', 'Buy {} shares of {}'.format(str(quantity), str(stock.symbol)))
                    context.turnover_count += 1
                    # adjust local cash value after placing each order
                    # any orders placed in zipline during a backtest are executed at next day before handle_Data is
                    # called. This is a default feature of zipline and is present to prevent any forward looking bias
                    # Hence the cash has to be managed locally
                    # next day morning can also be placed alongwith the sale orders.
                    cash -= quantity * data.current(stock, 'price')
                    # checking if the sector os the stocks is already part of our sectors list
                    if context.sector_stocks.get(sector, None) is None:
                        # if yes, updating the list of stocks for that sector
                        context.sector_stocks.update({sector: [stock]})
                    else:
                        # if no, adding that sector as well to our existing list
                        context.sector_stocks[sector].append(stock)
                        # printing buy order details
                    print("Buy order triggered for: {} on {} for {} shares"
                          .format(stock.symbol, data.current_dt.strftime('%d/%m/%Y'), quantity))
                # updating our local list of positions so that we do not cross the max 25 stock limit
                position_list.append(stock)
                # limit the max position to 25 at all stages
                if len(position_list) >= 25:
                    break


def handle_data(context, data):
    """
    handle_data carries the most important logic of the algorithm, this is the function where actual calculations for
    buying and selling takes place
    :param context: global variable used through the backtest for carrying forwarding the parameter values to next day
    :param data: mandatory to call as part of scheduled function, unused in our case
    :return: None
    """
    # get the list of current positions and store it in the local variable called positions
    positions = list(context.portfolio.positions.values())
    # get the stop list and store it in the local variable called stop_list
    stop_list = context.stop_loss_list

    # update stop loss list
    # the for loop goes through all the stocks of stop_list and reduces their no buy list days by 1 until it reaches 0.
    # If the no buy list days becomes 0, the stock is removed from the stop_loss_list and is allowed to be bought again
    for i1, s1 in stop_list.items():
        stop_list = stop_list.drop(index=[i1])
        s1 -= 1
        if s1 > 0:
            stop_list = stop_list.append(pd.Series([s1], index=[i1]))

    benchmark_dma = get_dma_returns(context, dma, data.current_dt)
    if benchmark_dma < 0:
        sell_all(positions, context)
        return

    # Sell logic
    # initialize an empty list of positions, used during the buy logic
    position_list = []
    # loop through all the positions in the portfolio
    for position in positions:
        # update the position_list as the loop runs everytime
        position_list.append(position.asset)
        # calculate the net percentage change for the stock
        net_gain_loss = float("{0:.2f}".format((position.last_sale_price - position.cost_basis)*100/position.cost_basis))
        # if the net change is less then -5%, trigger stop loss rule and sell the stock
        if net_gain_loss < -3:
            # order_target is a zipline function that allows to place orders based on the target number of stocks that
            # needs to be achieved in the portfolio. So order_target(xyz, 5) = will put a buy/sell order for xyx stock
            # such that afer the execution of the order there will be 5 shares of xyz in our portfolio. Similarly,
            # order_target(xyz, 0) -> will sell all the quantities of xyz present in the portfolio
            order_target(position.asset, 0)
            strategy.SendMessage('Sell Order', 'Buy all shares of {}'.format(str(position.asset.symbol)))
            context.turnover_count += 1

            # Sometimes, even though the orders are placed, some stocks are not sold on the execution days because of
            # multiple reasons linked to the market condition. Since we had the stock to our sector list while placing
            # the order itself we need to catch te exception in case the order fails and we retry to to remove it from
            # the list again on the next day
            try:
                context.sector_stocks[context.pipeline_data.loc[position.asset].sector].remove(position.asset)

                print("Stop loss triggered for: " + position.asset.symbol)
                # add to stop loss list to prevent re-buy
                stop_loss = pd.Series([stop_loss_prevention_days], index=[position.asset])
                stop_list = stop_list.append(stop_loss)
            except Exception as e:
                print(e)

    # updating the global stop_loss_list with the locally maintained one
    context.stop_loss_list = stop_list
    print("Handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def get_quantity(portfolio_value, sector_wise_exposure, sector, price, cash):
    """
    The function calculates the maximum number of shares that can be bought based on our max sector exposure
    condition(15%), default exposure per stock (5%) and available cash
    :param portfolio_value: float, current net value of the portfolio
    :param sector_wise_exposure: dictionary, sector wise exposure
    :param sector: int, sector of the given stock
    :param price: float, yesterday's closing price for the stock
    :param cash: float, locally maintained available cash for the buy order
    :return: int, net quantity of shares that can be bought
    """
    # calculate available exposure based on available cash
    available_exposure = cash / portfolio_value
    # check for existing exposure to the sector
    if sector in sector_wise_exposure:
        sector_exposure = sector_wise_exposure.get(sector)
        # if the current exposure is less then max alowed exposure to a sector, proceed
        if sector_exposure < max_sector_exposure:
            # get minimum of available sector exposure, default share exposure and available cash exposure
            exposure = min(max_sector_exposure - sector_exposure, initial_exposure, available_exposure)
            exposure = round(exposure, 4)
            # update the sector wise exposure
            sector_wise_exposure[sector] += exposure
        else:
            # since max allowed exposure limit has already been reached, allowed new exposure should be 0
            exposure = 0
    else:
        # if the sector is not already present, take minimum of default share exposure and available cash exposure
        exposure = min(initial_exposure, available_exposure)
        # add sector to sector wise exposure
        sector_wise_exposure[sector] = exposure
    # calculate the quantity based on the targeted exposure and price of the stock
    quantity = int((exposure * portfolio_value) / price)
    return quantity


def sell_all(positions, context):
    print("Sell All rule triggered for "+str(len(positions)))
    for position in positions:
        order_target_percent(position.asset, 0)
        strategy.SendMessage('Sell All and Exit Market', 'Sell all shares of {}'.format(str(position.asset.symbol)))
        context.turnover_count += 1


def get_dma_returns(context, period, dma_end_date):
    returns = context.trading_environment.benchmark_returns[:dma_end_date]
    if returns.size > period:
        returns = 1 + returns[-period:]
    else:
        return 0
    dma_return = 100 * (returns.prod() - 1)
    return dma_return


if __name__ == '__main__':
    # converting date string to date
    start_date = pd.to_datetime(config.get('start_date'), format='%Y%m%d').tz_localize('UTC')
    end_date = pd.to_datetime(config.get('end_date'), format='%Y%m%d').tz_localize('UTC')

    parser = argparse.ArgumentParser(description='live mode.')
    parser.add_argument('--live_mode', help='True for live mode')
    args = parser.parse_args()

    # The run_algorithm is a function provided by zipline that initializes and calls all the functions like before_
    # trading_start, handle_data etc etc in the prescribed order, thereby running our backtest from the defined
    # start till the end date, doing all the buy and sells with the starting capital defined as capital_base and using
    # the data bundle defined as bundle (in our case quandl
    kwargs = {'start': start_date,
              'end': end_date,
              'initialize': initialize,
              'handle_data': handle_data,
              'analyze': analyze,
              'before_trading_start': before_trading_start,
              'bundle': 'quandl',
              'capital_base': config.get('capital_base'),
              'algo_name': 'mid_term_low_risk',
              'benchmark_symbol': config.get('benchmark_symbol')}

    if args.live_mode == 'True':
        print("Running in live mode.")
        kwargs['tws_uri'] = 'localhost:7497:1232'
        kwargs['live_trading'] = True

    strategy = Strategy(kwargs)
    strategy.run_algorithm()

    input("Press any key to exit")
