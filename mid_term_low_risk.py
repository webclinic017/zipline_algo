import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes
from zipline.pipeline import Pipeline
from zipline.api import (
    attach_pipeline,
    order_target_percent,
    symbol,
    pipeline_output,
    record,
    schedule_function,
)
import matplotlib.pyplot as plt
from utils.plot_util import plot_header, plot_performance, plot_portfolio_value

current_year = None

# stop loss non addition limit set to 5 days
stop_loss_prevention_days = 15


def initialize(context):
    # context.additional_data = pd.DataFrame.from_csv('test2.csv', index_col=['ticker'])
    # context.securities = []
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.stop_loss_list = pd.Series()


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
            # 'CAPEX': fd.CAPEX_MRQ,
            'ipoyear': sectors,
            'yoy_sales': fd.yoy_sales,
            'qoq_earnings': fd.qoq_earnings
        },
    )


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def handle_data(context, data):
    pipeline_data = context.pipeline_data
    stop_list = context.stop_loss_list

    # remove assests with no market cap
    interested_assets = pipeline_data.dropna(subset=['marketcap'])

    # filter assets based on
    # 1. market cap is large cap (>10billion)
    # 2. liabilities < 180bn
    # 3. yoy sales > 6%
    # 4. ipo should be earlier than at least two years
    # 5. should have invested more than or equal 6% of total revenue in RND
    # 6. net income should be positive
    # 7. pe should be between 15 and 60
    # 8. should not have a decrease in earnings
    interested_assets = interested_assets.query("marketcap > 10000000000 "
                                                "and liabilities < 180000000000 "
                                                "and (yoy_sales >= 0.03 or yoy_sales != yoy_sales)"
                                                "and (ipoyear < {} or ipoyear == -1)"
                                                "and ((100 * rnd) / revenue) >= 6"
                                                "and netinc > 0"
                                                "and (15 <= pe <= 60)"
                                                "and qoq_earnings > 0"
                                                .format(data.current_dt.year - 2))

    positions = list(context.portfolio.positions.values())

    # updte stop loss list
    for i1, s1 in stop_list.items():
        stop_list = stop_list.drop(labels=[i1])
        s1 -= 1
        if s1 > 0:
            stop_list = stop_list.append(pd.Series([s1], index=[i1]))

    position_list = []
    for position in positions:
        position_list.append(position.asset)
        # sell at stop loss
        gain_loss = float("{0:.2f}".format((position.last_sale_price - position.cost_basis)*100/position.cost_basis))
        if gain_loss < -3:
            order_target_percent(position.asset, 0)
            print("Stop loss triggered for: "+position.asset.symbol)
            # add to stop loss list to prevent re-buy
            stop_loss = pd.Series([stop_loss_prevention_days], index=[position.asset])
            stop_list = stop_list.append(stop_loss)
        elif gain_loss >= 24:
            order_target_percent(position.asset, 0)
            print("Profit booked for: " + position.asset.symbol)
        else:
            print("Gain/Loss of " + str(gain_loss)+"% in stock " + position.asset.symbol)

    if len(position_list) < 25:
        for stock in interested_assets.index.values:
            # only buy if not part of positions already
            if stock not in position_list and stock not in stop_list:
                # buy order (5% of net portfolio)
                order_target_percent(stock, 0.05)
                print("Buy order triggered for: "+stock.symbol+" on "+data.current_dt.strftime('%m/%d/%Y'))
                position_list.append(stock)
                # limit the max position to 25 at all stages
                if len(position_list) >= 25:
                    break

    context.stop_loss_list = stop_list
    print("Handle data processed for {}".format(data.current_dt.strftime('%m/%d/%Y')))


def analyze(context, results):
    # add a grid to the plots
    plt.rc('axes', grid=True)
    plt.rc('grid', color='0.75', linestyle='-', linewidth=0.5)
    # adjust the font size
    plt.rc('font', size=7)

    plot_header(context, results)
    plot_performance(context, results, 311)
    plot_portfolio_value(context, results, 312)

    # render the plots
    plt.tight_layout(pad=4, h_pad=1)
    plt.legend(loc=0)
    plt.show()


if __name__ == '__main__':
    start_date = '20080331'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    end_date = '20180326'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data, analyze=analyze,
                            before_trading_start=before_trading_start, bundle='quandl', capital_base=100000)

    print(results)
