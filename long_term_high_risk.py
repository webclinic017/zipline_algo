import pandas as pd
from zipline.utils.run_algo import run_algorithm
from alphacompiler.data.sf1_fundamentals import Fundamentals
from alphacompiler.data.NASDAQ import NASDAQSectorCodes, NASDAQIPO
from zipline.pipeline import Pipeline
import logging
import datetime
import matplotlib.pyplot as plt
from zipline.utils.events import date_rules, time_rules
import numpy as np
from zipline.api import (
    get_datetime,
    attach_pipeline,
    order_target_percent,
    order_target,
    pipeline_output,
    record,
    schedule_function,
    get_environment,
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

# stop loss non addition limit set to 5 days
stop_loss_prevention_days = 15
# max exposure per sector set to 15%
max_sector_exposure = 0.15
fig, ax = plt.subplots(figsize=(10, 5), nrows=3, ncols=2)

name = "mt_hr_{}.log".format(str(datetime.datetime.now().strftime("%d_%m_%Y %H_%M_%S")))
logging.basicConfig(filename=name, level=logging.INFO)


def initialize(context):
    global fig, ax
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.stop_loss_list = pd.Series()

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
        ('algodd', 'float'),
        ('benchmarkdd', 'float'),
        ('leverage', 'int'),
        ('num_pos', 'int'),
    ]))
    port_history.set_index('date')
    context.port_history = port_history

    context.monthly_df = pd.DataFrame()
    context.annual_df = pd.DataFrame()
    context.turnover_count = 0

    # record variables every day after market close
    schedule_function(recordvars,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close())

    # scheduling the monthly function to be called at end of each month
    schedule_function(
        monthly_records,
        date_rule=date_rules.month_end()
    )

    fig.tight_layout()
    fig.show()
    fig.canvas.draw()
    context.ax = ax
    context.fig = fig


def analyze(context, data):
    print("Finalize is called")
    monthly_freq = context.monthly_df.pct_change().fillna(0)
    logging.info("Monthly Returns and Drawdowns")
    all_history = context.port_history.reset_index()
    for index, row in monthly_freq.iterrows():
        logging.info("{} Return: {}%".format(index.strftime('%b %Y'), str(round(row['portfolio_net']*100, 2))))

        current_month_loc = context.monthly_df.index.get_loc(index)
        if current_month_loc != 0:
            max_dd = all_history[(all_history['index'] <= index) &
                                 (all_history['index'] > context.monthly_df.iloc[current_month_loc - 1].name)]['algodd'].min()
            logging.info("{} Max dd: {}%".format(index.strftime('%b %Y'), str(round(max_dd))))

    logging.info("Annual Returns and Drawdowns")
    annual_freq = context.annual_df.pct_change().fillna(0)
    for index, row in annual_freq.iterrows():
        logging.info("{} Return: {}%".format(index.strftime('%Y'), str(round(row['portfolio_net'] * 100, 2))))

        current_year_loc = context.annual_df.index.get_loc(index)
        if current_year_loc != 0:
            max_dd = all_history[(all_history['index'] <= index) &
                                 (all_history['index'] > context.annual_df.iloc[current_year_loc - 1].name)][
                'algodd'].min()
            logging.info("{} Max dd: {}%".format(index.strftime('%Y'), str(round(max_dd))))


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

    if context.monthly_df.empty:
        context.monthly_df = context.port_history[-1:]
    if context.annual_df.empty:
        context.annual_df = context.port_history[-1:]

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


def monthly_records(context, data):
    history = context.port_history[-1:]
    context.monthly_df = context.monthly_df.append(history)
    if history.index.strftime('%m')[0] == '12':
        context.annual_df = context.annual_df.append(history)

        logging.info("{} Turnover count: {}".format(history.index.strftime('%Y')[0], context.turnover_count))
        # Reset Turnover count
        context.turnover_count = 0


def rebalance(context, data):
    positions = list(context.portfolio.positions.values())
    cash = context.portfolio.cash
    stop_list = context.stop_loss_list
    pipeline_data = context.pipeline_data

    recalc_sector_wise_exposure(context)

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
        exposure = (position.last_sale_price * position.amount) / net
        # selling half to book profit
        if exposure > 0.15:
            order_target_percent(position.asset, exposure / 2)
            context.turnover_count += 1
            print("Half profit booking done for {}".format(position.asset.symbol))

    position_list = []
    for position in positions:
        position_list.append(position.asset)

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
                    order_target(stock, quantity)
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
        net_gain_loss = float("{0:.2f}".format((position.last_sale_price - position.cost_basis)*100/position.cost_basis))
        if net_gain_loss < -3:
            order_target(position.asset, 0)
            context.turnover_count += 1
            try:
                context.sector_stocks[context.pipeline_data.loc[position.asset].sector].remove(position.asset)
            except Exception as e:
                print(e)

            print("Stop loss triggered for: "+position.asset.symbol)
            # add to stop loss list to prevent re-buy
            stop_loss = pd.Series([stop_loss_prevention_days], index=[position.asset])
            stop_list = stop_list.append(stop_loss)

    context.stop_loss_list = stop_list
    print("Daily handle data processed for {}".format(data.current_dt.strftime('%d/%m/%Y')))


def get_exposure(portfolio_value, sector_wise_exposure, sector, price, cash):
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
        context.turnover_count += 1


def get_dma_returns(context, period, dma_end_date):
    dma_start_date = dma_end_date - datetime.timedelta(days=period)
    returns = 1 + context.trading_environment.benchmark_returns.loc[dma_start_date: dma_end_date]
    if returns.size < 50:
        return 0
    dma_return = 100 * (returns.prod() - 1)
    return dma_return


if __name__ == '__main__':
    start_date = '20000101'
    start_date = pd.to_datetime(start_date, format='%Y%m%d').tz_localize('UTC')

    end_date = '20180331'
    end_date = pd.to_datetime(end_date, format='%Y%m%d').tz_localize('UTC')

    results = run_algorithm(start_date, end_date, initialize, handle_data=handle_data, analyze=analyze,
                            before_trading_start=before_trading_start, bundle='quandl', capital_base=100000)
    plot_alpha_beta(ax[2, 1], results)
    plot_sharpe(ax[2, 0], results)
    fig.canvas.draw()
    input("Press any key to exit")
