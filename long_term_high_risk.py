import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
import datetime
import matplotlib.pyplot as plt
from zipline.utils.events import date_rules, time_rules
import numpy as np
from zipline.api import (
    get_datetime,
    attach_pipeline,
    order_target,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
    get_environment,
)
from utils.plot_util import (
    plot_header,
    plot_performance,
    plot_portfolio_value,
    plot_returns,
    plot_drawdown,
    plot_positions_leverage,
    plot_relative_strength,
    get_benchmark_returns
)

# stop loss non addition limit set to 15 days
stop_loss_prevention_days = 15


def initialize(context):
    # prev day securities
    context.prev_long_univ = pd.DataFrame()
    context.long_univ_returns = 0
    context.advance_decline = 0

    context.long_market_env = 0
    context.hitrate_latest = 0
    context.num_pos_residuals = 0

    context.market_exposure_df = None

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

    # set up dataframe to record equity with loan value history
    port_history = pd.DataFrame(np.empty(0, dtype=[
        ('date', 'datetime64[ns]'),
        ('portfolio_net', 'float'),
        ('returns', 'float'),
        ('long_univ_returns', 'float'),
        ('hitrate', float),
        ('algodd', 'float'),
        ('univdd', 'float'),
        ('benchmarkdd', 'float'),
        ('leverage', 'int'),
        ('num_pos', 'int'),
        ('univ_len', 'int'),
        ('advance_decline', 'int'),
        ('num_pos_residuals', 'int'),
        ('advance_decline_std', 'float'),
        ('univ_rs', 'float')
    ]))
    port_history.set_index('date')
    context.port_history = port_history

    # record variables every day after market close
    schedule_function(recordvars,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close())

    fig, ax = plt.subplots(figsize=(10, 5), nrows=2, ncols=2)
    fig.tight_layout()
    fig.show()
    fig.canvas.draw()
    context.ax = ax
    context.fig = fig


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


def recordvars(context, data):
    date = get_datetime()
    port_history = context.port_history

    portfolio_net = context.account.equity_with_loan
    num_pos = len(context.portfolio.positions)
    leverage = context.account.leverage
    today_long_univ_return = context.long_univ_returns
    hr = context.hitrate_latest
    advance_decline = context.advance_decline

    port_history.set_value(date, 'portfolio_net',portfolio_net)
    port_history.set_value(date, 'long_univ_returns', today_long_univ_return)
    port_history.set_value(date, 'leverage', leverage)
    port_history.set_value(date, 'num_pos', num_pos)
    port_history.set_value(date, 'univ_len', len(context.prev_long_univ))
    port_history.set_value(date, 'hitrate', hr)
    # num of positions in univ and not in portfolio
    port_history.set_value(date, 'num_pos_residuals',context.num_pos_residuals)
    port_history.set_value(date, 'advance_decline', advance_decline)

    advance_decline_std = port_history['advance_decline'][-63:].std()
    port_history.set_value(date, 'advance_decline_std', advance_decline_std)

    today_return = port_history['portfolio_net'][-2:].pct_change().fillna(0)[-1]
    port_history.set_value(date, 'returns', today_return)

    max_net = port_history['portfolio_net'].max()
    algodd = min(0, 100 * (portfolio_net - max_net) / max_net)
    port_history.set_value(date, 'algodd', algodd)

    long_univ_returns = port_history['long_univ_returns']

    algo_returns_cum = 100 * ((1 + port_history['returns']).cumprod() - 1)
    long_univ_returns_cum = 100 * ((1 + long_univ_returns).cumprod() - 1)

    univdd = min(0, 100 * (((long_univ_returns_cum[-1]) - max(long_univ_returns_cum)) ) / (100+max(long_univ_returns_cum)))
    port_history.set_value(date, 'univdd', univdd)

    benchmark_returns = 1 + get_benchmark_returns(context)
    benchmark_returns_cum = 100 * (benchmark_returns.cumprod() - 1)
    benchmarkdd = min(0, 100 * (((benchmark_returns_cum[-1]) - max(benchmark_returns_cum))) / (100 + max(benchmark_returns_cum)))
    port_history.set_value(date, 'benchmarkdd', benchmarkdd)
    if len(long_univ_returns_cum) > 1 :
        port_history.set_value(date, 'univ_rs', (1 + (long_univ_returns_cum[-1]/100)) / (1+ (benchmark_returns_cum[-1]/100)))
    else :
        port_history.set_value(date, 'univ_rs', 1.0)

    record(leverage=leverage, num_pos=num_pos)

    # log.info('Backtest date: ' +  context.datetime.strftime('%Y-%m-%d') + ' Long Univ(' + str(len(context.prev_long_univ)) + ')='
    #     + '{:.2f}'.format(long_univ_returns_cum[-1]) + ' Algo(' + str(num_pos) + ')=' + '{:.2f}'.format(algo_returns_cum[-1]) + ' DD=' + '{:.2f}'.format(algodd)
    #     + ' A/D=' + str(advance_decline))

    # if we have more than 1 month history update the equity curve plot
    if get_environment('arena') == 'backtest' and len(port_history) % 10 == 0:
        ax = context.ax
        fig = context.fig

        plot_returns(ax[0, 0], algo_returns_cum,long_univ_returns_cum, benchmark_returns_cum)
        plot_drawdown(ax[0, 1], port_history['algodd'], port_history['univdd'], port_history['benchmarkdd'])
        plot_positions_leverage(ax[1, 0], port_history['num_pos'], port_history['univ_len'], port_history['leverage'], port_history['num_pos_residuals'])
        # plot_exposure(ax[1, 1], port_history['leverage'])
        plot_relative_strength(ax[1, 1], port_history['univ_rs'])
        # plot_hitrate(ax[2, 0], port_history['hitrate'])
        # plot_adline(ax[2, 1], port_history['advance_decline'])

        fig.canvas.draw()  # draw
        plt.pause(0.01)


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


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def handle_data(context, data):
    positions = list(context.portfolio.positions.values())
    cash = context.portfolio.cash
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
            order_target(position.asset, 0)
            cash += (position.last_sale_price * position.amount)
            # TODO: fix for order not going through
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
                price = data.history(stock, 'price', 1, '1d').item()
                sector = interested_assets.loc[stock].sector
                quantity = get_exposure(context.portfolio.portfolio_value,
                                        context.sector_wise_exposure, sector, price, cash)

                if quantity > 0 and data.can_trade(stock):
                    # buy order
                    order_target(stock, quantity)
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

    context.stop_loss_list = stop_list
    print("Handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def get_exposure(portfolio_value, sector_wise_exposure, sector, price, cash):
    available_exposure = cash / portfolio_value
    if sector in sector_wise_exposure:
        sector_exposure = sector_wise_exposure.get(sector)
        if sector_exposure < 0.15:
            exposure = min(0.15 - sector_exposure, 0.05, available_exposure)
            exposure = round(exposure, 4)
            sector_wise_exposure[sector] += exposure
        else:
            exposure = 0
    else:
        exposure = min(0.05, available_exposure)
        sector_wise_exposure[sector] = exposure
    quantity = int((exposure * portfolio_value) / price)
    return quantity


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
