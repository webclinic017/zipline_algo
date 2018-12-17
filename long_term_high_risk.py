import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
from zipline.api import (
    attach_pipeline,
    order_target_percent,
    symbol,
    pipeline_output,
    record,
    schedule_function,
)
import datetime
import matplotlib.pyplot as plt
from utils.plot_util import plot_header, plot_performance, plot_portfolio_value
from zipline.utils.events import date_rules

current_year = None

# stop loss non addition limit set to 5 days
stop_loss_prevention_days = 15


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.stop_loss_list = pd.Series()

    context.long_mavg_days = 200
    context.short_mavg_days = 50
    context.sector_wise_exposure = dict()
    context.sector_stocks = {}

    schedule_function(
        rebalance,
        date_rule=date_rules.month_start()
    )


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


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def handle_data(context, data):
    positions = list(context.portfolio.positions.values())
    recalc_sector_wise_exposure(context)

    pipeline_data = context.pipeline_data
    stop_list = context.stop_loss_list

    # remove assets with no market cap
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

    # update stop loss list
    for i1, s1 in stop_list.items():
        stop_list = stop_list.drop(index=[i1])
        s1 -= 1
        if s1 > 0:
            stop_list = stop_list.append(pd.Series([s1], index=[i1]))

    # Sell logic
    position_list = []
    for position in positions:
        position_list.append(position.asset)
        # sell at stop loss
        net_gain_loss = float("{0:.2f}".format((position.last_sale_price - position.cost_basis)*100/position.cost_basis))
        if net_gain_loss < -3:
            order_target_percent(position.asset, 0)
            # TODO: fix for order target not going through
            try:
                context.sector_stocks[context.pipeline_data.loc[position.asset].sector].remove(position.asset)
            except Exception as e:
                print(e)

            print("Stop loss triggered for: "+position.asset.symbol)
            # add to stop loss list to prevent re-buy
            stop_loss = pd.Series([stop_loss_prevention_days], index=[position.asset])
            stop_list = stop_list.append(stop_loss)

    # Buy logic
    if len(position_list) < 25:
        for stock in interested_assets.index.values:
            # only buy if not part of positions already
            if stock not in position_list and stock not in stop_list:
                avg_vol = data.history(stock, 'volume', 50, '1d').mean()
                if avg_vol < 10000:
                    continue
                # buy order
                exposure = get_exposure(context.sector_wise_exposure, interested_assets.loc[stock].sector)
                if exposure > 0.01 and data.can_trade(stock):
                    order_target_percent(stock, exposure)
                    if context.sector_stocks.get(interested_assets.loc[stock].sector, None) is None:
                        context.sector_stocks.update({interested_assets.loc[stock].sector: [stock]})
                    else:
                        context.sector_stocks[interested_assets.loc[stock].sector].append(stock)
                    print("Buy order triggered for: {} on {} for {} %"
                          .format(stock.symbol, data.current_dt.strftime('%m/%d/%Y'), round(exposure * 100, 2)))
                position_list.append(stock)
                # limit the max position to 25 at all stages
                if len(position_list) >= 25:
                    break

    context.stop_loss_list = stop_list
    print("Handle data processed for {}".format(data.current_dt.strftime('%m/%d/%Y')))


def recalc_sector_wise_exposure(context):
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


def rebalance(context, data):
    net = context.portfolio.portfolio_value
    for position in context.portfolio.positions.values():
        exposure = (position.last_sale_price * position.amount) / net
        # selling half to book profit
        if exposure > 0.15:
            order_target_percent(position.asset, exposure / 2)
            print("Half profit booking done for {}".format(position.asset.symbol))


def get_exposure(sector_wise_exposure, sector):
    if sector in sector_wise_exposure:
        sector_exposure = sector_wise_exposure.get(sector)
        if sector_exposure < 0.15:
            exposure = min(0.15 - sector_exposure, 0.05)
            exposure = round(exposure, 4)
            sector_wise_exposure[sector] += exposure
            return exposure
        else:
            return 0
    else:
        sector_wise_exposure[sector] = 0.05
        return 0.05


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


def sell_all(positions):
    print("Sell All rule triggered for "+str(len(positions)))
    for position in positions:
        order_target_percent(position.asset, 0)


def get_dma_returns(context, period, dma_end_date):
    dma_start_date = dma_end_date - datetime.timedelta(days=period)
    returns = 1 + context.trading_environment.benchmark_returns.loc[dma_start_date: dma_end_date]
    dma_return = 100 * (returns.prod() - 1)
    # dma_return = context.trading_environment.benchmark_returns.loc[dma_start_date: dma_end_date].sum()
    return dma_return


if __name__ == '__main__':
    start_date = '20080331'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    end_date = '20180326'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data, analyze=analyze,
                            before_trading_start=before_trading_start, bundle='quandl', capital_base=100000)

    print(results)
