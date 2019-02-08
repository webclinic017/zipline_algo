import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
import matplotlib.pyplot as plt
from zipline.utils.events import date_rules, time_rules
import numpy as np
from cvxopt import solvers, matrix
from zipline.api import (
    get_datetime,
    attach_pipeline,
    order_target_percent,
    order_target,
    pipeline_output,
    record,
    schedule_function,
    get_environment
)
from utils.plot_util import (
    plot_returns,
    plot_drawdown,
    plot_positions,
    plot_leverage,
    get_benchmark_returns,
    plot_alpha_beta,
    plot_sharpe
)

# stop loss non addition limit set to 15 days
stop_loss_prevention_days = 15

# max exposure per sector set to 15%
max_sector_exposure = 0.15
fig, ax = plt.subplots(figsize=(10, 5), nrows=3, ncols=2)


def initialize(context):
    global fig, ax
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.stop_loss_list = pd.Series()
    context.sector_wise_exposure = dict()
    context.sector_stocks = {}
    context.keep_list = []

    schedule_function(
        rebalance,
        date_rule=date_rules.month_start()
    )

    port_history = pd.DataFrame(np.empty(0, dtype=[
        ('date', 'datetime64[ns]'),
        ('portfolio_net', 'float'),
        ('returns', 'float'),
        ('algodd', 'float'),
        ('benchmarkdd', 'float'),
        ('leverage', 'int'),
        ('num_pos', 'int'),
    ]))
    port_history.set_index('date')
    context.port_history = port_history

    schedule_function(recordvars,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close())

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


def recalc_sector_wise_exposure(context):
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
    positions = list(context.portfolio.positions.values())
    pipeline_data = context.pipeline_data
    context.keep_list = []
    # cash = context.portfolio.cash
    # stop_list = context.stop_loss_list
    # recalc_sector_wise_exposure(context)
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

    position_list = []
    for position in positions:
        position_list.append(position.asset)
        net_gain_loss = float(
            "{0:.2f}".format((position.last_sale_price - position.cost_basis) * 100 / position.cost_basis))
        if net_gain_loss > 10:
            context.keep_list.append(position.asset)

    assets = interested_assets.index.tolist()
    assets.extend(context.keep_list)
    stock_price = data.history(list(set(assets)), 'close', 365, '1d')

    stock_price_return = stock_price.pct_change()[1:]

    stock_price_return = stock_price_return[(stock_price_return.T != 0).any()]

    stock_price_skew = stock_price_return.skew(skipna=True)

    stock_list = [i for i, v in stock_price_skew.items() if v > 0]

    stock_list.extend(context.keep_list)

    stock_list = sorted(list(set(stock_list)))

    stock_returns = stock_price_return[stock_list]

    # start portfolio construction
    P = stock_returns.cov()
    P = matrix(P.get_values())

    q = matrix(np.zeros((len(stock_list), 1)))

    n = len(stock_list)
    sector_data = interested_assets.loc[stock_list, 'sector'].fillna(-1).to_dict()
    sectors = int(max(list(sector_data.values())))
    stocks = list(sector_data.keys())
    stocks.sort()

    G = np.identity(n,dtype=float)
    G = G * -1
    positive_identity = np.identity(n ,dtype=float)
    # G = np.concatenate((negative_identity, positive_identity))

    for i in range(-1, sectors + 1):
        l = [-1. if sector_data[stocks[x]] == i else 0. for x in range(n)]
        if -1. in l:
            G = np.vstack([G, l])

    G = matrix(G)

    # h
    h = [.0] * n
    # h.extend([0.15] * n)
    h.extend([0.3] * (G.size[0] - n))
    h = matrix(h, (len(h), 1))

    A = matrix(1.0, (1, n))
    b = matrix(1.0)

    try:
        sol = solvers.qp(P, q, G, h, A, b)
    except:
        return

    weights = list(sol['x'])

    stock_weights = dict(zip(stocks, weights))
    stock_weights = pd.Series(stock_weights)

    kelly = (stock_returns.mean() / (stock_returns.std() ** 2)) / 2

    kelly = kelly.clip(0.75, 1)
    stock_weights[stock_weights < 0.01] = 0
    stock_weights = stock_weights.multiply(kelly)

    # get weights of holdings
    holdings_weight = dict()
    for asset, position in context.portfolio.positions.items():
        holdings_weight.update({asset: (position['cost_basis'] * position['amount']) / context.account.equity_with_loan})

    holdings_weight = pd.Series.from_array(holdings_weight)
    new_stocks_weights = stock_weights[stock_weights > 0]
    final_stocks_weights = pd.DataFrame(
        dict(holdings_weight=holdings_weight, new_stocks_weights=new_stocks_weights)).fillna(0)

    final_stocks_weights['weight'] = final_stocks_weights['new_stocks_weights'] - final_stocks_weights['holdings_weight']

    for asset, row in final_stocks_weights.iterrows():
        order_target_percent(asset, round(row['new_stocks_weights'], 4))

    print("Handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def recordvars(context, data):
    date = get_datetime()
    port_history = context.port_history

    portfolio_net = context.account.equity_with_loan
    num_pos = len(context.portfolio.positions)
    leverage = context.account.leverage

    port_history.set_value(date, 'portfolio_net', portfolio_net)
    port_history.set_value(date, 'leverage', leverage)
    port_history.set_value(date, 'num_pos', num_pos)

    today_return = port_history['portfolio_net'][-2:].pct_change().fillna(0)[-1]
    port_history.set_value(date, 'returns', today_return)

    max_net = port_history['portfolio_net'].max()
    algodd = min(0, 100 * (portfolio_net - max_net) / max_net)
    port_history.set_value(date, 'algodd', algodd)

    algo_returns_cum = 100 * ((1 + port_history['returns']).cumprod() - 1)

    benchmark_returns = 1 + get_benchmark_returns(context)
    benchmark_returns_cum = 100 * (benchmark_returns.cumprod() - 1)
    benchmarkdd = min(0, 100 * ((benchmark_returns_cum[-1]) - max(benchmark_returns_cum)) / (
            100 + max(benchmark_returns_cum)))
    port_history.set_value(date, 'benchmarkdd', benchmarkdd)

    record(leverage=leverage, num_pos=num_pos)

    # if we have more than 1 month history update the equity curve plot
    if get_environment('arena') == 'backtest' and len(port_history) % 10 == 0:
        ax = context.ax
        fig = context.fig

        plot_returns(ax[0, 0], algo_returns_cum, benchmark_returns_cum)
        plot_drawdown(ax[0, 1], port_history['algodd'], port_history['benchmarkdd'])
        plot_positions(ax[1, 0], port_history['num_pos'])
        plot_leverage(ax[1, 1], port_history['leverage'])
        fig.canvas.draw()  # draw
        plt.pause(0.01)


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def handle_data(context, data):
    for asset, position in context.portfolio.positions.items():
        pctGL = (position.last_sale_price / position.cost_basis) - 1
        if pctGL <= -0.08:
            order_target(asset, 0)


if __name__ == '__main__':
    start_date = '20090331'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')
    end_date = '20180326'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data,
                            before_trading_start=before_trading_start, bundle='quandl', capital_base=100000)

    plot_alpha_beta(ax[2, 1], results)
    plot_sharpe(ax[2, 0], results)
    fig.canvas.draw()
    print(results)
