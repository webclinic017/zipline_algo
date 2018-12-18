#
# Copyright 2017 Data Analysis, Inc.import matplotlib.pyplot as plt
#
import matplotlib.pyplot as plt


def plot_header(context, results, unit='$', with_ending_cash=False):
    """Plot backtest header"""
    fig = plt.figure(1, dpi=160, facecolor='white')

    date_fmt = '%Y-%m-%d'
    fig.suptitle('Backtest from {start_date} to {end_date} with {unit}{capital_base:0,.2f} capital base'.format(
        start_date=context.sim_params.start_session.strftime(date_fmt),
        end_date=context.sim_params.end_session.strftime(date_fmt),
        unit=unit,
        capital_base=context.sim_params.capital_base
    ))
    if with_ending_cash:
        ending_cash = float(results.tail(1).ending_cash)
        fig.text(0.01, 0.01, 'Ending cash (approximately): {unit}{ending_cash:0,.2f}'.format(
            unit=unit, ending_cash=ending_cash))

    fig.subplots_adjust(top=0.88)


def plot_grid_lines():
    """Add basic gridlines to the plots"""
    # add a grid to the plots
    plt.rc('axes', grid=True)
    plt.rc('grid', color='0.75', linestyle='-', linewidth=0.5)
    # adjust the font size
    plt.rc('font', size=7)


def plot_performance(context, results, grid, offset=0):
    """Plot performance (%) against benchmark

    If offset is provided, the first offset count will be dropped.
    The remaining DataFrame will be normalized to the first
    remaining item after offset.
    """
    plot = plt.subplot(grid)
    plot.set_ylabel('Performance (%)')
    algorithm_returns = results.algorithm_period_return * 100
    algorithm_returns.plot(ax=plot, color='b', linewidth=0.7)

    benchmark_returns = results.benchmark_period_return
    if offset:
        benchmark_returns = benchmark_returns.drop(results.head(offset).index)
        # normalize to 0
        benchmark_returns = benchmark_returns - benchmark_returns.values[0]

    benchmark_returns = benchmark_returns * 100
    benchmark_returns.plot(ax=plot, color='#9c9c9c', linewidth=0.7)
    plt.legend(loc=0)


def plot_portfolio_value(context, results, grid, unit='$'):
    """Plot the portfolio cash value"""
    plot = plt.subplot(grid)  # 2 rows, one column, first plot
    results.portfolio_value.plot(ax=plot, color='b', linewidth=0.7)
    plot.set_ylabel('Portfolio value in ({unit})'.format(unit=unit))
    plt.legend(loc=0)


def plot_volatility(context, results, grid):
    """Plot volatility against benchmark"""
    plot = plt.subplot(grid)
    plot.set_ylabel('Volatility')
    results.algo_volatility.plot(ax=plot, color='b', linewidth=0.7)
    results.benchmark_volatility.plot(ax=plot, color='#9c9c9c', linewidth=0.7)
    plt.legend(loc=0)


def plot_alpha_beta(context, results, grid):
    """Plot alpha and beta"""
    plot = plt.subplot(grid)
    plot.set_ylabel('alpha/beta')
    results.alpha.plot(ax=plot, color='c', linewidth=0.7)
    results.beta.plot(ax=plot, color='m', linewidth=0.7)
    plt.legend(loc=0)


def plot_sortino(context, results, grid):
    """Plot sortino value"""
    plot = plt.subplot(grid)
    plot.set_ylabel('Sortino')
    results.sortino.plot(ax=plot, color='m', linewidth=0.7)
    plt.legend(loc=0)


def plot_positions(context, results, grid):
    """Plot number of shorts and longs"""
    plot = plt.subplot(grid)
    plot.set_ylabel('Positions')
    results.longs_count.plot(ax=plot, color='g', linewidth=0.7)
    results.shorts_count.plot(ax=plot, color='r', linewidth=0.7)
    plt.legend(loc=0)


def plot_params(params):
    """Plot the parameters used for the backtest

    Parameters
    ----------
    params : dict

    Returns
    -------
    None, plots on the matplotlib figure
    """
    figure_text = ', '.join(['{}: {}'.format(k, v) for k, v in params.items()])
    plt.figtext(0.01, 0.01, figure_text, backgroundcolor='#eeeeee', size='small')


def plot_returns(plt, returns, benchmark_returns):
        plt.clear()
        algo_line = plt.plot(returns, color='black', label='Algo')
        benchmark_line = plt.plot(benchmark_returns, color='gray', label='Benchmark')
        plt.tick_params(reset=True, length=6)
        plt.legend(handles=[algo_line[0], benchmark_line[0]], loc='upper left', fontsize='small')
        plt.set_title('Returns')
        plt.grid(color='gray', linestyle='solid')


def plot_drawdown(plt, algodd, benchmarkdd):
        plt.clear()
        plt.locator_params(axis='x', nticks=6)
        algo_line = plt.plot(algodd, color='black', label='Algo')
        benchmark_line = plt.plot(benchmarkdd, color='gray', label='Benchmark')

        plt.legend(handles=[algo_line[0], benchmark_line[0]], loc='lower left', fontsize='small')
        plt.set_title('Drawdown')
        plt.grid(color='gray', linestyle='solid')


def plot_positions_leverage(plt, num_pos, leverage):
        plt.clear()
        plt.locator_params(axis='x', nticks=6)
        numpos_line = plt.plot(num_pos, color='black', label='Algo')
        leverage_line = plt.plot(100 * leverage, color='green', label='Leverage')

        plt.legend(handles=[numpos_line[0], leverage_line[0]], loc='lower left', fontsize='small')
        plt.set_title('Positions & Leverage')
        plt.grid(color='gray', linestyle='solid')


def get_benchmark_returns(context):
    return context.trading_environment.benchmark_returns.loc[context.sim_params.start_session: context.datetime]