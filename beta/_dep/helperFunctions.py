# Module Imports
import pandas as pd
from datetime import timedelta
import operator
import itertools
from functools import partial, reduce
import zipline
import zipline.api
from zipline.api import get_open_orders, cancel_order, order_target, set_commission, \
    set_long_only, symbols, order_target_percent, get_order, get_datetime
from zipline.finance import commission

import logging
import math


# HELPER FUNCTIONS

fst = lambda tup:tup[0]
snd = lambda tup:tup[1]


def get_all_open_orders():
    return reduce(operator.add, map(snd, get_open_orders().iteritems()), [])


def get_orders_for_stock(stock):
    orders = get_all_open_orders()
    return filter(lambda o:o.sid == stock and o.amount != 0, orders)


def check_if_no_conflicting_orders(stock):
    # Check that we are not already trying to move this stock
    return len(get_orders_for_stock(stock)) == 0


def check_invalid_positions(context, securities):
    # Check that the portfolio does not contain any broken positions
    # or external securities
    for sid, position in context.portfolio.positions.iteritems():
        if sid not in securities and position.amount != 0:
            errmsg = \
                "Invalid position found: {sid} amount = {amt} on {date}".format(sid = position.sid,
                                                                                amt = position.amount,
                                                                                date = get_datetime())
            raise Exception(errmsg)


def do_cancel_order(context, sym, do_delete, order):
    logging.info("X CANCELED {0:s} with {1:,d} / {2:,d} filled" \
             .format(sym,
                     order.filled,
                     order.amount))
    cancel_order(order)
    if do_delete:
        del context.duration[order.id]


def close_orders_after_time(context, stock, currentTime):
    # Ensure that the orders are not open past its desired duration.
    #  For live trading you could replace this with VWAPBestEffort,
    #  https://www.quantopian.com/help#api-VWAPBestEffort

    f = lambda o:o.id in context.duration and context.duration[o.id] <= currentTime
    map(partial(do_cancel_order, context, stock.symbol, True), filter(f, get_orders_for_stock(stock)))


def end_of_day(context, data):
    # cancel any order at the end of day. Do it ourselves so we can see slow moving stocks.

    logging.info("")
    logging.info("* EOD: Stoping Orders & Printing Held *")
    logging.info("")

    # Print what positions we are holding overnight
    for stock in data:
        if context.portfolio.positions[stock.sid].amount != 0:
            logging.info("{0:s} has remaining {1:,d} Positions worth ${2:,.2f}" \
                     .format(stock.symbol,
                             context.portfolio.positions[stock.sid].amount,
                             context.portfolio.positions[stock.sid].cost_basis \
                             * context.portfolio.positions[stock.sid].amount))

    # Cancel any open orders ourselves(In live trading this would be done for us, soon in backtest too)
    open_orders = get_all_open_orders()
    map(partial(do_cancel_order, context, stock.symbol, False),
        open_orders)  # stock here just happens to be last one in list (is that truly what is desired?)


def fire_sale(context, data):
    # Sell everything in the portfolio, at market price
    logging.info("# Fire Sale #")
    for stock in data:
        if context.portfolio.positions[stock.sid].amount != 0:
            order_target(stock, 0.0)
            value_of_open_orders(context, data)
            availibleCash = context.portfolio.cash - context.cashCommitedToBuy - context.cashCommitedToSell
            logging.info("- SELL {0:,d} of {1:s} at ${2:,.2f} for ${3:,.2f} / ${4:,.2f}" \
                     .format(context.portfolio.positions[stock.sid].amount,
                             stock.symbol,
                             data[stock]['price'],
                             data[stock]['price'] * context.portfolio.positions[stock.sid].amount,
                             availibleCash))


def percent_diff(val1, val2):
    return abs(val1 - val2) / ((val1 + val2) / 2.0)


def value_of_open_orders(context, data):
    # current cash commited to open orders
    context.currentCash = context.portfolio.cash
    open_orders = get_open_orders()
    context.cashCommitedToBuy = 0.0
    context.cashCommitedToSell = 0.0
    if open_orders:
        for security, orders in open_orders.iteritems():
            for oo in orders:
                # estimate value of existing order with current price, best to use order conditons?
                # logging.info(oo.amount * data[oo.sid]['price'])
                if (oo.amount > 0):
                    context.cashCommitedToBuy += oo.amount * data[oo.sid]['price']
                elif (oo.amount < 0):
                    context.cashCommitedToSell += oo.amount * data[oo.sid]['price']


# END HELPER FUNCTIONS

# For the sake of example, define some universe and apply the helper fucntions to illustrate their use.
def initialize(context):
    # Manually define stocks instead of downloading a universe with Fetch or using a cross section with set_universe
    context.stocks = symbols('AAPL', 'IBM', 'CSCO', 'SYN')

    # Dictionary of durations, optional for any order
    context.duration = { }

    # Inside the data loop, keep track of commited cash for the new orders.
    #  The portfolio cash is not updated on an intra cycle time scale yet.
    context.cashCommitedToBuy = 0
    context.cashCommitedToSell = 0

    # set a more realistic commission for IB
    set_commission(commission.PerShare(cost = 0.014, min_trade_cost = 1.4))

    # Prevent shorting, not needed here but it will stop
    #  runaway code, like if you buy condition goes nuts
    #  borrowing uncontrollably.
    set_long_only()

    logging.info("---Prices below reflect market price or average held value at time of action and" +
             " NOT the value of the transactions. Use the Run Full Backtest" +
             " button and view the transactions tab to view real prices.---")


# Will be called on every trade event for the securities you specify.
def handle_data(context, data):
    # Get EST Time
    exchange_time = pd.Timestamp(get_datetime()).tz_convert('US/Eastern')

    # Check that our portfolio does not  contain any invalid/external positions/securities
    check_invalid_positions(context, data)

    # Perform a fire sale the next morning, since we held a couple positions overnight
    if exchange_time.day == 3:
        if (exchange_time.hour == 9 and exchange_time.minute == 31):
            fire_sale(context, data)
        # The backtester only allows for a two day test currently, lets just trade on 7/2/2014
        return
    #

    # Print portfolio state at the start and enc of the day
    if (exchange_time.hour == 9 and exchange_time.minute == 31) or \
            (exchange_time.hour == 16):
        value_of_open_orders(context, data)
        logging.info("")
        logging.info("** Cash: ${0:,.2f} | Capital: ${1:,.2f} | BUY:{2:,.2f} | SELL: ${3:,.2f} **"
                 .format(context.portfolio.cash,
                         context.portfolio.capital_used,
                         context.cashCommitedToBuy,
                         context.cashCommitedToSell))
        logging.info("")
    #

    # End of day
    if exchange_time.hour == 15 and exchange_time.minute == 55:
        # Close all orders, print open positions(cause our goal was to not have any at end of day)
        end_of_day(context, data)

        # exit handle_data here to prevent more trading
        return
    #

    # For this time event, act on each security in the portfolio
    for stock in data:

        # Ensure that the orders are not open past its desired duration.
        #  For live trading you could replace this with VWAPBestEffort, https://www.quantopian.com/help#api-VWAPBestEffort
        close_orders_after_time(context, stock, exchange_time)

        # If no price data for this stock this event cycle, we cant act(data[stock]['price'] will throw error)
        if not 'price' in data[stock]:
            # No price in this time step!
            logging.info("X Could not fetch price for {0:s} at {1:d}:{2:d}" \
                     .format(data[stock]['price'],
                             exchange_time.hour,
                             exchange_time.minute))
            # skip to next stock in data
            continue

        # Lets BUY each of our stocks in the morning,
        #  using a fixed time is not ideal but we only
        #  want to place a single order per stock this script
        if exchange_time.hour == 9 and exchange_time.minute == 31:

            # No exiting positions this script cause we used a fix time and no previous positons,
            #  but as a habbit lets make sure we dont already have MOVE for this stock
            if check_if_no_conflicting_orders(stock) and context.portfolio.positions[stock.sid].amount == 0:
                # Partition the portfolio cash equally among the universe
                orderId = order_target_percent(stock, 1.0 / len(data))
                shareCount = get_order(orderId).amount

                # example, lets set a duration time for SYN to avoid price drift with slow fill rates
                if stock.symbol == 'SYN':
                    context.duration[orderId] = exchange_time + timedelta(minutes = 60)

                value_of_open_orders(context, data)
                availibleCash = context.portfolio.cash - context.cashCommitedToBuy - context.cashCommitedToSell

                # NOTE: the reported price here is the current market price,
                #  depending on order style the actual transaction could
                #  be occuring after a price change.
                #  Check out order types in doc: https://www.quantopian.com/help#api-order-methods
                logging.info("+ BUY {0:,d} of {1:s} at ${2:,.2f} for ${3:,.2f} / ${4:,.2f}" \
                         .format(shareCount,
                                 stock.symbol, data[stock]['price'],
                                 data[stock]['price'] * shareCount,
                                 availibleCash))

        # Toward the end of the day, lets exitt our positions. Again the use of a fixed time is for example only
        if exchange_time.hour == 15 and exchange_time.minute == 30:

            # Ensure no conflicting position or orders before we BUY
            if check_if_no_conflicting_orders(stock) and context.portfolio.positions[stock.sid].amount != 0:
                # Take this position to zero(exit, entierly, the Buy or Short)
                order_target(stock, 0.0)

                value_of_open_orders(context, data)
                availibleCash = context.portfolio.cash - context.cashCommitedToBuy - context.cashCommitedToSell

                # NOTE: the reported price here is the current market price,
                #  depending on order style the actual transaction could
                #  be occuring after a price change.
                #  Check out order types in doc: https://www.quantopian.com/help#api-order-methods
                logging.info("- SELL {0:,d} of {1:s} at ${2:,.2f} for ${3:,.2f} / ${4:,.2f}" \
                         .format(context.portfolio.positions[stock.sid].amount,
                                 stock.symbol,
                                 data[stock]['price'],
                                 data[stock]['price'] * context.portfolio.positions[stock.sid].amount,
                                 availibleCash))
                # Just for illustration in the logs, lets "accidently" hold a position overnight as well as an open order.
        if exchange_time.hour == 15 and exchange_time.minute == 45:
            # So after we have sold, lets just take a position in order
            #  to see what happens if we hold position at end of
            #  day, same for open order of SYN
            if stock.symbol == 'AAPL' or stock.symbol == 'SYN':
                # Ensure no conflicting position or orders before we BUY
                if check_if_no_conflicting_orders(stock) and context.portfolio.positions[stock.sid].amount == 0:
                    orderId = order_target_percent(stock, 0.1)
                    shareCount = get_order(orderId).amount
                    value_of_open_orders(context, data)
                    availibleCash = context.portfolio.cash - context.cashCommitedToBuy - context.cashCommitedToSell
                    logging.info("+ BUY {0:,d} of {1:s} at ${2:,.2f} for ${3:,.2f} / ${4:,.2f}" \
                             .format(shareCount,
                                     stock.symbol, data[stock]['price'],
                                     data[stock]['price'] * shareCount,
                                     availibleCash))
