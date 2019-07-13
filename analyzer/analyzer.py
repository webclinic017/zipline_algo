import datetime
import os
import sys
from pathlib import Path

import empyrical
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from pandas.tseries.offsets import BDay

from analyzer.analysis_data import AnalysisData
from analyzer.views.main import AnalyzerWindow
import zipline


class Analyzer:
    def __init__(self, strategy):
        self.sector_file = 'NASDAQ_sids.npy'
        self.sector_data = np.load(os.path.join(str(Path.home()), self.sector_file))
        self.sector_code_mapping = {0: "Basic Industries",
                                    1: "Capital Goods",
                                    2: "Consumer Durables",
                                    3: "Consumer Non-Durables",
                                    4: "Consumer Services",
                                    5: "Energy",
                                    6: "Finance",
                                    7: "Health Care",
                                    8: "Miscellaneous",
                                    9: "Public Utilities",
                                    10: "Technology",
                                    11: "Transportation"}
        self.app = QtWidgets.QApplication(sys.argv)
        self.daily_data_df = pd.DataFrame(columns=['date', 'net', 'benchmark_net'])
        self.daily_cagr = pd.Series()
        self.daily_benchmark_cagr = pd.Series()
        self.daily_data_df.set_index('date', inplace=True)
        self.daily_positions_df = pd.DataFrame(columns=['position_date',
                                                        'date',
                                                        'symbol',
                                                        'name',
                                                        'entry',
                                                        'exit',
                                                        'sector',
                                                        'quantity',
                                                        'avg_price',
                                                        'last_price',
                                                        'daily_change',
                                                        'pct_daily_change',
                                                        'total_change',
                                                        'pct_total_change',
                                                        'pct_port'])
        self.daily_positions_df.set_index(['date', 'symbol'], inplace=True)

        self.transactions_data = pd.DataFrame(
            columns=['counter', 'date', 'symbol', 'company_name', 'transaction_type', 'quantity', 'avg_price'])
        self.transaction_count = 0

        self.analysis_data = AnalysisData()
        self.strategy = strategy

        self.analysis_data.info_data['algo_name'] = self.strategy.strategy_data.get('algo_name')
        self.analysis_data.info_data['initial_cash'] = self.strategy.strategy_data.get('capital_base')
        self.analysis_data.info_data['benchmark_symbol'] = self.strategy.strategy_data.get('benchmark_symbol')
        self.aw = AnalyzerWindow(self.analysis_data, self.strategy.strategy_data, self.app)

    def initialize(self):
        pass

    def before_trading_start(self):
        pass

    def handle_data(self, context):
        print("Processing - {}".format(context.datetime.date().strftime("%Y%m%d")))
        self.aw.current_date = context.datetime.date()
        previous_date = context.datetime.date() if self.daily_data_df.empty else self.daily_data_df.index[-1]
        previous_days_position = \
            self.daily_positions_df.loc[self.daily_positions_df.index.get_level_values('date') == previous_date]

        if self.daily_data_df.empty:
            self.daily_data_df.loc[context.datetime.date()] = [context.account.equity_with_loan,
                                                               context.account.equity_with_loan]
        else:
            benchmark_return = context.trading_environment.benchmark_returns.loc[context.datetime.date()]
            benchmark_net = self.daily_data_df.iloc[-1].benchmark_net + \
                            (self.daily_data_df.iloc[-1].benchmark_net * benchmark_return)
            self.daily_data_df.loc[context.datetime.date()] = [context.account.equity_with_loan,
                                                               benchmark_net]

        columns = ['position_date',
                   'name',
                   'entry',
                   'exit',
                   'sector',
                   'quantity',
                   'avg_price',
                   'last_price',
                   'daily_change',
                   'pct_daily_change',
                   'total_change',
                   'pct_total_change',
                   'pct_port']

        for position in context.portfolio.positions.values():
            if (previous_date, position.asset.symbol) in previous_days_position.index:
                previous_last_price = self.daily_positions_df.loc[previous_date, position.asset.symbol].last_price
                daily_change = position.last_sale_price - previous_last_price
                pct_daily_change = position.last_sale_price / previous_last_price - 1
                entry = self.daily_positions_df.loc[previous_date, position.asset.symbol].entry
            else:
                daily_change = 0
                pct_daily_change = 0
                entry = context.datetime.date()
            pct_port = position.last_sale_price * position.amount / context.account.equity_with_loan
            total_change = position.last_sale_price - position.cost_basis
            pct_total_change = position.last_sale_price / position.cost_basis - 1
            self.daily_positions_df.loc[(context.datetime.date(),
                                    position.asset.symbol), columns] = [context.datetime.date(),
                                                                        position.asset.asset_name,
                                                                        entry,
                                                                        '',
                                                                        self.sector_code_mapping.get(
                                                                   self.sector_data[
                                                                       position.asset.sid],
                                                                   'NA'),
                                                               position.amount,
                                                               position.cost_basis,
                                                               position.last_sale_price,
                                                               daily_change,
                                                               pct_daily_change,
                                                               total_change,
                                                               pct_total_change,
                                                               pct_port
                                                               ]

        if len(context.metrics_tracker._ledger._processed_transactions) > 0:
            for date, transactions in context.metrics_tracker._ledger._processed_transactions.items():
                for transaction in transactions:
                    self.transaction_count += 1
                    amount = transaction.get('amount')
                    type = 'Buy' if amount > 0 else 'Sell'
                    order_id = transaction.get('order_id')
                    symbol = transaction.get('sid').symbol
                    asset_name = transaction.get('sid').asset_name
                    price = transaction.get('price')
                    self.transactions_data.at[order_id] = [self.transaction_count, date.date(), symbol, asset_name, type, amount, price]
                    # check if symbol does not exists in position
                    if zipline.api.symbol(symbol) not in context.portfolio.positions.keys():
                        self.daily_positions_df.loc[(previous_date, symbol), 'exit'] = context.datetime.date()

        self.generate_analysis_data(context)

        if self.daily_data_df.shape[0] % 21 == 0:
            self.aw.updateSignal.emit(self.analysis_data)

    def generate_analysis_data(self, context):

        if self.daily_data_df.shape[0] > 0:
            # Calculate returns
            daily_returns = self.daily_data_df['net'].pct_change()

            # daily return for the first day will always be 0
            daily_returns[0] = (self.daily_data_df['net'][0] / self.analysis_data.info_data['initial_cash']) - 1

            ytd_returns = daily_returns[
                daily_returns.index >= datetime.datetime(daily_returns.index[-1].year, 1, 1).date()]

            one_year_daily_returns = daily_returns[daily_returns.index >= (daily_returns.index[-1] - BDay(252)).date()]

            benchmark_returns = context.trading_environment.benchmark_returns.loc[
                                self.daily_data_df.index[0]:self.daily_data_df.index[-1]]
            benchmark_returns.index = benchmark_returns.index.date

            daily_returns = daily_returns.drop(daily_returns.index.difference(benchmark_returns.index))
            benchmark_returns = benchmark_returns.drop(benchmark_returns.index.difference(daily_returns.index))

            ytd_benchmark_returns = benchmark_returns[
                benchmark_returns.index >= datetime.datetime(benchmark_returns.index[-1].year, 1, 1).date()]

            one_year_benchmark_returns = benchmark_returns[
                benchmark_returns.index >= (benchmark_returns.index[-1] - BDay(252)).date()]

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
            cagr = empyrical.cagr(daily_returns)
            print(cagr)
            report_dict['cagr'] = cagr
            report_dict['std'] = daily_returns.std() * 100

            benchmark_report_dict['total_return_pct'] = (benchmark_returns + 1).prod() - 1
            benchmark_report_dict['total_return'] = self.daily_data_df.iloc[-1].benchmark_net \
                                                    - self.daily_data_df.iloc[0].benchmark_net
            benchmark_report_dict['ytd'] = (ytd_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['one_year'] = (one_year_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['max_drawdown'] = benchmark_dd.min()
            benchmark_report_dict['sharpe_ratio'] = empyrical.sharpe_ratio(benchmark_returns)
            benchmark_report_dict['alpha'], benchmark_report_dict['beta'] = 0, 1
            benchmark_report_dict['cagr'] = empyrical.cagr(benchmark_returns)
            benchmark_report_dict['std'] = benchmark_returns.std() * 100

            self.daily_cagr[daily_returns.index[-1]] = report_dict['cagr']
            self.daily_benchmark_cagr[benchmark_returns.index[-1]] = benchmark_report_dict['cagr']

            plot_data_df = pd.concat([daily_returns, benchmark_returns], axis=1,
                                     keys=['returns', 'benchmark_returns'])

            plot_data_df.reset_index(inplace=True)

            plot_data_df['drawdown'] = portfolio_dd
            plot_data_df['benchmark_drawdown'] = benchmark_dd

            plot_data_df.set_index('date', inplace=True)
            plot_data_df['cagr'] = self.daily_cagr
            plot_data_df['benchmark_cagr'] = self.daily_benchmark_cagr
            plot_data_df['positions_count'] = self.daily_positions_df.groupby('date').size()
            plot_data_df['positions_count'] = plot_data_df['positions_count'].fillna(0)

            self.analysis_data.chart_data = plot_data_df
            self.analysis_data.strategy_report = report_dict
            self.analysis_data.benchmark_report = benchmark_report_dict
            if len(self.daily_positions_df.index.get_level_values('date').value_counts()) < 30:
                self.analysis_data.holdings_data = self.daily_positions_df.reset_index()
            else:
                self.analysis_data.holdings_data = self.daily_positions_df.loc[self.daily_positions_df.index.get_level_values('date') >= self.daily_positions_df.index.get_level_values('date').value_counts().sort_index().index[-30]].reset_index()
            if len(self.daily_data_df.index) < 30:
                self.analysis_data.monthly_transactions_data = self.transactions_data
            else:
                self.analysis_data.monthly_transactions_data = self.transactions_data[self.transactions_data.date >= self.daily_data_df.index[-30]]
            self.analysis_data.holdings_data_historical = self.daily_positions_df.reset_index()
            self.analysis_data.transactions_data = self.transactions_data

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
            (returns.shape[0] + 1,) + returns.shape[1:],
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
        self.aw.enable_date_range_selection()

    def show_plot(self):
        self.aw.show()
