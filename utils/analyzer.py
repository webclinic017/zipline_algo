import datetime
import empyrical
import numpy as np
from utils.analysis_data import AnalysisData
from utils.window import AnalyzerWindow
import pandas as pd
from pandas.tseries.offsets import BDay
from PyQt5 import QtWidgets
import sys


APPROX_BDAYS_PER_YEAR = 252


class BackTestAnalyzer:
    def __init__(self, strategy):
        super().__init__()

        self.strategyApp = QtWidgets.QApplication(sys.argv)

        # create daily data dataframe
        self.daily_data_df = pd.DataFrame(columns=['date', 'net', 'long_positions', 'short_positions',
                                  'long_exposure', 'short_exposure'])
        self.daily_data_df.set_index('date', inplace=True)

        self.strategy = strategy

        # initialize the analysis_Data object
        self.analysis_data = AnalysisData()
        self.analysis_data.info_data['algo_name'] = self.strategy.algo_name
        self.analysis_data.info_data['backtest_name'] = self.strategy.backtest_name
        self.analysis_data.info_data['backtest_description'] = self.strategy.backtest_description
        self.analysis_data.info_data['backtest_user'] = self.strategy.backtest_user
        self.analysis_data.info_data['backtest_machine'] = self.strategy.backtest_machine

        self.analysis_data.info_data['backtest_startdate'] = self.strategy.context.get('start_date')
        self.analysis_data.info_data['backtest_enddate'] = self.strategy.context.get('end_date')

        self.analysis_data.info_data['backtestrun_starttime'] = datetime.datetime.now()
        self.analysis_data.info_data['benchmark_symbol'] = self.strategy.data_portal.get_benchmark_symbol()
        self.analysis_data.info_data['initial_cash'] = self.strategy.broker.get_init_cash()

        self.aw = AnalyzerWindow(self.analysis_data, self.strategyApp)
        # self.aw.setWindowTitle("Strategy Backtest")

        self.__plot_update_frequency = 21
        if self.__plot_update_frequency is None or self.__plot_update_frequency == 0:
            self.__plot_update_frequency = 21

    def show_plot(self):
        self.aw.show()

    def get_report(self):
        return self.__report

    def get_benchmark_report(self):
        return self.__benchmark_report

    def initialize(self):
        super().initialize()

    def after_trading_end(self, date):
        # logger.info("BackTestAnalyzer after_trading_end")
        portfolio = self.strategy.broker.portfolio()
        event_stats = self.strategy.broker._BacktestBroker__event_stats_df

        # Calculate long, short positions
        long_positions = 0
        short_positions = 0
        total_long_market_value = 0
        total_short_market_value = 0
        for instrument, position in portfolio.positions.items():
            if position.quantity > 0:
                long_positions += 1
                total_long_market_value += position.market_value
            else:
                short_positions += 1
                total_short_market_value += position.market_value

        # Calculate Leverage
        total_long_exposure = total_long_market_value / portfolio.net
        total_short_exposure = total_short_market_value / portfolio.net

        self.daily_data_df.loc[date] = [portfolio.net, long_positions, short_positions,
                                            total_long_exposure, total_short_exposure]

        # check if time to plot the returns
        if self.daily_data_df.shape[0] % self.__plot_update_frequency == 0:
            # calculate metrics for plot
            self.generate_analysis_data()

            # send update the plot event
            self.aw.updateSignal.emit(self.analysis_data)

    def calculate_roundtrip_metrics(self):
        roundtrip_df = self.strategy.broker.get_roundtrips()

        winners_percent = None
        if not roundtrip_df.empty :
            winners = roundtrip_df.loc[roundtrip_df['pnl'] >= 0]
            losers = roundtrip_df.loc[roundtrip_df['pnl'] < 0]
            #equals = roundtrip_df.loc[roundtrip_df['pnl'] == 0]
            winners_percent = winners.shape[0] / roundtrip_df.shape[0]
            losers_percent = losers.shape[0] / roundtrip_df.shape[0]
            avg_winners_duration = winners.days_held.mean()
            avg_losers_duration = losers.days_held.mean()
            avg_winners_return = winners['return'].mean()
            avg_losers_return = losers['return'].mean()

            #TODO: add current positions to win/loss status

            #print("winners_percent={:.2f}, avg_winners_duration={:.2f}, avg_losers_duration={:.2f}, avg_winners_return={:.2f}, avg_losers_return={:.2f}"
            #        .format(winners_percent, avg_winners_duration, avg_losers_duration, avg_winners_return, avg_losers_return) )

        return winners_percent

    def rolling_drawdown(self, returns):
        """
        calculate the rollowing drawdown for a given returns
        """
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
            dtype='float64',
        )
        cumulative[0] = start = 100
        empyrical.cum_returns(returns_array, starting_value=start, out=cumulative[1:])

        max_return = np.fmax.accumulate(cumulative, axis=0)

        out = (cumulative - max_return) / max_return
        out = pd.Series(out[1:])

        return out

    def generate_analysis_data(self):
        self.analysis_data.info_data['num_universe_symbols'] = len(self.strategy.data_portal.get_cache_instruments())
        self.analysis_data.info_data['backtest_asofdate'] = self.strategy.context.get('cur_date')

        self.analysis_data.orders_data = self.strategy.broker.get_orders()
        self.analysis_data.roundtrip_data = self.strategy.broker.get_roundtrips()
        self.analysis_data.warnings_data = self.strategy.broker.warnings

        self.analysis_data.event_stats = self.strategy.broker._BacktestBroker__event_stats_df
        self.analysis_data.event_tracks = self.strategy.broker._BacktestBroker__event_track_df

        self.analysis_data.market_regime = self.strategy.broker._BacktestBroker__market_regime_df
        self.analysis_data.user_data = self.strategy.broker._BacktestBroker__user_data_df

        # calculate roundtrip metrics
        win_rate = self.calculate_roundtrip_metrics()

        if self.daily_data_df.shape[0] > 0:
            # Calculate returns
            daily_returns = self.daily_data_df['net'].pct_change()

            # daily return for the first day will always be 0
            daily_returns[0] = (self.daily_data_df['net'][0] / self.analysis_data.info_data['initial_cash']) - 1

            ytd_returns = daily_returns[daily_returns.index >= datetime.datetime(daily_returns.index[-1].year, 1, 1)]

            one_year_daily_returns = daily_returns[daily_returns.index >=
                                                   (daily_returns.index[-1] - BDay(APPROX_BDAYS_PER_YEAR))]
            three_years_daily_returns = daily_returns[daily_returns.index >=
                                                      (daily_returns.index[-1] - BDay(3 * APPROX_BDAYS_PER_YEAR))]
            five_years_daily_returns = daily_returns[daily_returns.index >=
                                                     (daily_returns.index[-1] - BDay(5 * APPROX_BDAYS_PER_YEAR))]
            ten_years_daily_returns = daily_returns[daily_returns.index >=
                                                    (daily_returns.index[-1] - BDay(10 * APPROX_BDAYS_PER_YEAR))]

            benchmark_returns = self.strategy.data_portal.get_benchmark_returns(from_date=self.daily_data_df.index[0])

            ytd_benchmark_returns = benchmark_returns[benchmark_returns.index >=
                                                      datetime.datetime(benchmark_returns.index[-1].year, 1, 1)]

            one_year_benchmark_returns = benchmark_returns[benchmark_returns.index >=
                                                           (benchmark_returns.index[-1] - BDay(APPROX_BDAYS_PER_YEAR))]
            three_years_benchmark_returns = benchmark_returns[benchmark_returns.index >=
                                                              (benchmark_returns.index[-1] -
                                                               BDay(3 * APPROX_BDAYS_PER_YEAR))]
            five_years_benchmark_returns = benchmark_returns[benchmark_returns.index >=
                                                             (benchmark_returns.index[-1] -
                                                              BDay(5 * APPROX_BDAYS_PER_YEAR))]
            ten_years_benchmark_returns = benchmark_returns[benchmark_returns.index >=
                                                            (benchmark_returns.index[-1] -
                                                             BDay(10 * APPROX_BDAYS_PER_YEAR))]

            # calculate rolling max_drawdown
            portfolio_dd = self.rolling_drawdown(daily_returns.values)
            benchmark_dd = self.rolling_drawdown(benchmark_returns.values)

            report_dict = {}
            benchmark_report_dict = {}
            # calculate portfolio report
            report_dict['total_return'] = (daily_returns + 1).prod() - 1
            report_dict['ytd'] = (ytd_returns + 1).prod() - 1
            report_dict['one_year'] = (one_year_daily_returns + 1).prod() - 1
            report_dict['three_years'] = (three_years_daily_returns + 1).prod() - 1
            report_dict['five_years'] = (five_years_daily_returns + 1).prod() - 1
            report_dict['ten_years'] = (ten_years_daily_returns + 1).prod() - 1
            report_dict['max_drawdown'] = portfolio_dd.min()
            report_dict['sharpe_ratio'] = empyrical.sharpe_ratio(daily_returns)
            report_dict['sortino_ratio'] = empyrical.sortino_ratio(daily_returns)
            report_dict['alpha'], report_dict["beta"] = empyrical.alpha_beta_aligned(daily_returns, benchmark_returns)
            report_dict['cagr'] = empyrical.cagr(daily_returns)
            report_dict['correlation'] = daily_returns.corr(other=benchmark_returns)
            report_dict['std'] = daily_returns.std() * 100
            report_dict['win_rate'] = (win_rate * 100) if win_rate else None
            report_dict['calmar'] = empyrical.calmar_ratio(daily_returns)
            report_dict['omega'] = empyrical.omega_ratio(daily_returns)
            report_dict['tail'] = empyrical.tail_ratio(daily_returns)
            report_dict['downside'] = empyrical.downside_risk(daily_returns)
            report_dict['up_capture'] = empyrical.up_capture(daily_returns, benchmark_returns)
            report_dict['down_capture'] = empyrical.down_capture(daily_returns, benchmark_returns)
            report_dict['up_down'] = empyrical.up_down_capture(daily_returns, benchmark_returns)
            report_dict['ann_volatility'] = empyrical.annual_volatility(daily_returns)
            report_dict['excess_sharpe'] = empyrical.excess_sharpe(daily_returns, benchmark_returns)
            # logger.info(report_dict)

            # calculate Benchmark report
            benchmark_report_dict['total_return'] = (benchmark_returns + 1).prod() - 1
            benchmark_report_dict['ytd'] = (ytd_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['one_year'] = (one_year_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['three_years'] = (three_years_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['five_years'] = (five_years_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['ten_years'] = (ten_years_benchmark_returns + 1).prod() - 1
            benchmark_report_dict['max_drawdown'] = benchmark_dd.values.min() # empyrical.max_drawdown(benchmark_returns)
            benchmark_report_dict['sharpe_ratio'] = empyrical.sharpe_ratio(benchmark_returns)
            benchmark_report_dict['sortino_ratio'] = empyrical.sortino_ratio(benchmark_returns)
            benchmark_report_dict['alpha'] = 0
            benchmark_report_dict['beta'] = 1
            benchmark_report_dict['cagr'] = empyrical.cagr(benchmark_returns)
            benchmark_report_dict['correlation'] = 1
            benchmark_report_dict['std'] = benchmark_returns.std() * 100
            benchmark_report_dict['win_rate'] = None
            benchmark_report_dict['calmar'] = empyrical.calmar_ratio(benchmark_returns)
            benchmark_report_dict['omega'] = empyrical.omega_ratio(benchmark_returns)
            benchmark_report_dict['tail'] = empyrical.tail_ratio(benchmark_returns)
            benchmark_report_dict['downside'] = empyrical.downside_risk(benchmark_returns)
            benchmark_report_dict['ann_volatility'] = empyrical.annual_volatility(benchmark_returns)
            # logger.info(benchmark_report_dict)

            # prepare plot data
            plot_data_df = pd.concat([daily_returns, benchmark_returns,
                                     self.daily_data_df['long_positions'],  self.daily_data_df['short_positions'],
                                     self.daily_data_df['long_exposure'], self.daily_data_df['short_exposure']],
                                     axis=1,
                                     keys=['returns', 'benchmark_returns', 'long_positions', 'short_positions',
                                           'long_exposure', 'short_exposure'])
            plot_data_df.reset_index(inplace=True)
            plot_data_df['drawdown'] = portfolio_dd
            plot_data_df['benchmark_drawdown'] = benchmark_dd

            plot_data_df.set_index('date', inplace=True)

            # set the market_regime after date index is set
            if self.analysis_data.market_regime is not None and self.analysis_data.market_regime.shape[0] > 0:
                plot_data_df['regime_id'] = self.analysis_data.market_regime['regime_id'].fillna(method='ffill').astype(int)

            # concat the user_data after date index is set
            if self.analysis_data.user_data is not None and len(self.analysis_data.user_data.columns) > 0\
                    and self.analysis_data.user_data.shape[0] > 0:
                plot_data_df[self.analysis_data.user_data.columns] = self.analysis_data.user_data

            self.analysis_data.chart_data = plot_data_df

            self.analysis_data.strategy_report = report_dict
            self.analysis_data.benchmark_report = benchmark_report_dict

    def finalize(self):
        self.generate_analysis_data()
        self.analysis_data.info_data['backtestrun_endtime'] = datetime.datetime.now()
        # send update the plot event
        self.aw.updateSignal.emit(self.analysis_data)