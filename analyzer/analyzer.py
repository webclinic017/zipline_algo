from PyQt5 import QtWidgets
from analyzer.views.main import AnalyzerWindow
import sys
import pandas as pd
from analyzer.analysis_data import AnalysisData
import datetime
from pandas.tseries.offsets import BDay
import numpy as np
import empyrical


class Analyzer:
    def __init__(self, strategy):
        self.app = QtWidgets.QApplication(sys.argv)
        self.daily_data_df = pd.DataFrame(columns=['date', 'net'])
        self.daily_data_df.set_index('date', inplace=True)

        self.analysis_data = AnalysisData()
        self.strategy = strategy

        self.analysis_data.info_data['algo_name'] = self.strategy.strategy_data.get('algo_name')
        self.analysis_data.info_data['initial_cash'] = self.strategy.strategy_data.get('capital_base')
        self.analysis_data.info_data['benchmark_symbol'] = self.strategy.strategy_data.get('benchmark_symbol')
        self.aw = AnalyzerWindow(self.analysis_data, self.app)

    def initialize(self):
        pass

    def before_trading_start(self):
        pass

    def handle_data(self, context):
        self.daily_data_df.loc[context.datetime.date()] = [context.account.equity_with_loan]

        if self.daily_data_df.shape[0] % 21 == 0:
            self.generate_analysis_data(context)

            self.aw.updateSignal.emit(self.analysis_data)

    def generate_analysis_data(self, context):

        if self.daily_data_df.shape[0] > 0:

            # Calculate returns
            daily_returns = self.daily_data_df['net'].pct_change()

            # daily return for the first day will always be 0
            daily_returns[0] = (self.daily_data_df['net'][0] / self.analysis_data.info_data['initial_cash']) - 1

            ytd_returns = daily_returns[daily_returns.index >= datetime.datetime(daily_returns.index[-1].year, 1, 1).date()]

            one_year_daily_returns = daily_returns[daily_returns.index >= (daily_returns.index[-1] - BDay(252)).date()]

            benchmark_returns = context.trading_environment.benchmark_returns.loc[self.daily_data_df.index[0]:self.daily_data_df.index[-1]]
            benchmark_returns.index = benchmark_returns.index.date

            daily_returns = daily_returns.drop(daily_returns.index.difference(benchmark_returns.index))
            benchmark_returns = benchmark_returns.drop(benchmark_returns.index.difference(daily_returns.index))

            ytd_benchmark_returns = benchmark_returns[
                benchmark_returns.index >= datetime.datetime(benchmark_returns.index[-1].year, 1, 1).date()]

            one_year_benchmark_returns = benchmark_returns[benchmark_returns.index >= (benchmark_returns.index[-1] - BDay(252)).date()]

            portfolio_dd = self.rolling_drawdown(daily_returns.values)
            benchmark_dd = self.rolling_drawdown(benchmark_returns.values)

            report_dict = {}
            benchmark_report_dict = {}

            report_dict['total_return_pct'] = (daily_returns + 1).prod() - 1
            report_dict['total_return'] = self.daily_data_df.iloc[-1].net - self.daily_data_df.iloc[0].net
            report_dict['ytd'] = (ytd_returns + 1).prod() - 1
            report_dict['one_year'] = (one_year_daily_returns + 1).prod() - 1
            report_dict['max_drawdown'] = portfolio_dd.min()

            report_dict['sharpe_ratio'] = empyrical.sharpe_ratio(daily_returns)
            report_dict['alpha'], report_dict['beta'] = empyrical.alpha_beta_aligned(daily_returns, benchmark_returns)
            report_dict['cagr'] = empyrical.cagr(daily_returns)
            report_dict['std'] = daily_returns.std() * 100

            benchmark_report_dict['total_return_pct'] = (benchmark_returns + 1).prod() - 1
            benchmark_report_dict['total_return'] = 0
            benchmark_report_dict['ytd'] = (ytd_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['one_year'] = (one_year_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['max_drawdown'] = benchmark_dd.min()
            benchmark_report_dict['sharpe_ratio'] = empyrical.sharpe_ratio(benchmark_returns)
            benchmark_report_dict['alpha'], benchmark_report_dict['beta'] = 0, 1
            benchmark_report_dict['cagr'] = empyrical.cagr(benchmark_returns)
            benchmark_report_dict['std'] = benchmark_returns.std() * 100

            plot_data_df = pd.concat([daily_returns, benchmark_returns], axis=1,
                                     keys=['returns', 'benchmark_returns'])

            plot_data_df.reset_index(inplace=True)

            plot_data_df['drawdown'] = portfolio_dd

            plot_data_df['benchmark_drawdown'] = benchmark_dd

            plot_data_df.set_index('date', inplace=True)

            # holdings data
            holdings = pd.DataFrame(columns=['symbol',
                                             'name',
                                             'sector',
                                             'avg_price',
                                             'last_price',
                                             'daily_change',
                                             'pct_daily_change',
                                             'total_change',
                                             'pct_total_change',
                                             'pct_port'])

            holdings.at[0] = ['symbol',
                               'name',
                               'sector',
                               'avg_price',
                               'last_price',
                               'daily_change',
                               'pct_daily_change',
                               'total_change',
                               'pct_total_change',
                               'pct_port']

            self.analysis_data.chart_data = plot_data_df
            self.analysis_data.strategy_report = report_dict
            self.analysis_data.benchmark_report = benchmark_report_dict
            self.analysis_data.holdings_data = holdings

    def rolling_drawdown(self, returns):
        out = np.empty(returns.shape[1:])

        returns_1d = returns.ndim == 1

        if len(returns) < 1:
            out[()] = np.nan

            if returns_1d:
                out = out.item()

            return out

        returns_array = np.asanyarray(returns)

        cumulative = np.empty(
            (returns.shape[0] + 1, ) + returns.shape[1:],
            dtype='float64'
        )

        cumulative[0] = start = 100

        empyrical.cum_returns(returns_array, starting_value=start, out=cumulative[1:])

        max_return = np.fmax.accumulate(cumulative, axis=0)

        out = (cumulative - max_return) / max_return

        out = pd.Series(out[1:])

        return out

    def after_trading_end(self):
        pass

    def finalize(self):
        pass

    def show_plot(self):
        self.aw.show()
