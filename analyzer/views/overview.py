from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from analyzer.views.spinnerwidget import QtWaitingSpinner
from analyzer.views.group_box import GroupConfigBoxWidget
from PyQt5.QtGui import QColor
import itertools
import numpy as np
import copy


class OverviewTab(AnalysisTab):
    def __init__(self, parent, analysis_data):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.analysis_data = analysis_data
        self.plotter = OverviewWidget(self, analysis_data)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.plotter)
        self.setLayout(self.layout)

    def get_tab_name(self):
        return "Overview"

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return "Analyze Strategy metrics with comparison to benchmark metrics"

    def update_plot(self, analysis_data):
        self.analysis_data = analysis_data
        self.plotter.plot(analysis_data)

    def generate_report(self):
        report = {}

        # Returns Table
        # Assign 1st row as column headers
        returns_header = copy.copy(self.plotter.returns_labels)
        returns_header.insert(0, '')
        returns_table_data = [returns_header]
        # Add vertical columns
        row1_data = ['Strategy']
        row2_data = [self.analysis_data.info_data['benchmark_symbol']]
        # Add data
        for sr, br in zip(self.plotter.strategy_returns, self.plotter.benchmark_returns):
            row1_data.append(sr.text())
            row2_data.append(br.text())
        returns_table_data.append(row1_data)
        returns_table_data.append(row2_data)
        report['returns_table'] = returns_table_data

        # Ratios Table
        # Assign 1st row as column headers
        ratios_header = copy.copy(self.plotter.ratios_labels)
        ratios_header.insert(0, '')
        ratios_table_data = [ratios_header]
        # Add vertical columns
        row1_data = ['Strategy']
        row2_data = [self.analysis_data.info_data['benchmark_symbol']]
        # Add data
        for sr, br in zip(self.plotter.strategy_ratios, self.plotter.benchmark_ratios):
            row1_data.append(sr.text())
            row2_data.append(br.text())
        ratios_table_data.append(row1_data)
        ratios_table_data.append(row2_data)
        report['ratios_table'] = ratios_table_data

        # Volatility Table
        # Assign 1st row as column headers
        volatility_header = copy.copy(self.plotter.volatility_labels)
        volatility_header.insert(0, '')
        volatility_table_data = [volatility_header]
        # Add vertical columns
        row1_data = ['Strategy']
        row2_data = [self.analysis_data.info_data['benchmark_symbol']]
        # Add data
        for sv, bv in zip(self.plotter.strategy_volatility, self.plotter.benchmark_volatility):
            row1_data.append(sv.text())
            row2_data.append(bv.text())
        volatility_table_data.append(row1_data)
        volatility_table_data.append(row2_data)
        report['volatility_table'] = volatility_table_data

        return report


class OverviewWidget(QtWidgets.QTableWidget):
    def __init__(self, parent, analysis_data):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.analysis_data = analysis_data

        # configure layout
        grid = QtWidgets.QGridLayout()

        self.returns_widget = self.get_returns_widget()
        self.ratios_widget = self.get_ratio_widget()
        self.volatility_widget = self.get_volatility_widget()

        grid.addWidget(self.returns_widget, 0, 0)
        grid.addWidget(self.ratios_widget, 1, 0)
        grid.addWidget(self.volatility_widget, 2, 0)
        self.setLayout(grid)

        self.spinner = self.configure_spinner()
        self.spinner.start()

    def get_returns_widget(self):
        returns_widget = QtWidgets.QWidget()

        returns_layout = QtWidgets.QVBoxLayout(returns_widget)
        returns_gbox = GroupConfigBoxWidget('Returns', returns_widget, False)
        returns_grid = QtWidgets.QGridLayout()
        self.returns_labels = ['Returns (%)', 'Returns ($)', 'CAGR', 'YTD']

        self.strategy_returns = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0', self),
                                 QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self)]

        self.benchmark_returns = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('-', self),
                                  QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self)]

        for col, label, strategy_return, benchmark_return in zip(range(1, len(self.returns_labels) + 1),
                                                                 self.returns_labels,
                                                                 self.strategy_returns, self.benchmark_returns):
            returns_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>" + label + "</font></strong>"), 0,
                                   col)
            returns_grid.addWidget(strategy_return, 1, col)
            returns_grid.addWidget(benchmark_return, 2, col)

        returns_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>Strategy</font></strong>", self), 1, 0)
        returns_grid.addWidget(
            QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data['benchmark_symbol']
                             + "</font></strong>", self), 2, 0)
        returns_grid.setSpacing(0)
        returns_gbox.setLayout(returns_grid)

        returns_layout.setContentsMargins(0, 0, 0, 0)
        returns_layout.addWidget(returns_gbox)

        return returns_widget

    def get_ratio_widget(self):
        ratio_widget = QtWidgets.QWidget()

        ratio_layout = QtWidgets.QVBoxLayout(ratio_widget)
        ratio_gbox = GroupConfigBoxWidget('Ratios', ratio_widget, False)
        ratio_grid = QtWidgets.QGridLayout()
        self.ratios_labels = ['Alpha', 'Beta', 'Sharpe', 'Win Ratio']

        self.strategy_ratios = [QtWidgets.QLabel('0', self), QtWidgets.QLabel('0', self),
                                QtWidgets.QLabel('0', self), QtWidgets.QLabel('0', self)]

        self.benchmark_ratios = [QtWidgets.QLabel('0', self), QtWidgets.QLabel('0', self),
                                 QtWidgets.QLabel('0', self), QtWidgets.QLabel('0', self)]

        for col, label, strategy_return, benchmark_return in zip(range(1, len(self.ratios_labels) + 1),
                                                                 self.ratios_labels,
                                                                 self.strategy_ratios, self.benchmark_ratios):
            ratio_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>" + label + "</font></strong>"), 0,
                                 col)
            ratio_grid.addWidget(strategy_return, 1, col)
            ratio_grid.addWidget(benchmark_return, 2, col)

        ratio_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>Strategy</font></strong>", self), 1, 0)
        ratio_grid.addWidget(
            QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data['benchmark_symbol']
                             + "</font></strong>", self), 2, 0)

        ratio_grid.setSpacing(0)
        ratio_gbox.setLayout(ratio_grid)

        ratio_layout.setContentsMargins(0, 0, 0, 0)
        ratio_layout.addWidget(ratio_gbox)

        return ratio_widget

    def get_volatility_widget(self):
        volatility_widget = QtWidgets.QWidget()

        volatility_layout = QtWidgets.QVBoxLayout(volatility_widget)
        volatility_gbox = GroupConfigBoxWidget('Volatility', volatility_widget, False)
        volatility_grid = QtWidgets.QGridLayout()

        self.volatility_labels = ['Max Drawdown', 'Std Dev']

        self.strategy_volatility = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0', self)]

        self.benchmark_volatility = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0', self)]

        for col, label, strategy_return, benchmark_return in zip(range(1, len(self.volatility_labels) + 1),
                                                                 self.volatility_labels,
                                                                 self.strategy_volatility,
                                                                 self.benchmark_volatility):
            volatility_grid.addWidget(
                QtWidgets.QLabel("<font color='#666666'><strong>" + label + "</font></strong>"), 0, col)
            volatility_grid.addWidget(strategy_return, 1, col)
            volatility_grid.addWidget(benchmark_return, 2, col)

        volatility_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>Strategy</font></strong>", self),
                                  1, 0)
        volatility_grid.addWidget(
            QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data['benchmark_symbol']
                             + "</font></strong>", self), 2, 0)

        volatility_grid.setSpacing(0)
        volatility_gbox.setLayout(volatility_grid)

        volatility_layout.setContentsMargins(0, 0, 0, 0)
        volatility_layout.addWidget(volatility_gbox)

        return volatility_widget

    def configure_spinner(self):
        spinner = QtWaitingSpinner(self)

        spinner.setRoundness(70.0)
        spinner.setMinimumTrailOpacity(15.0)
        spinner.setTrailFadePercentage(70.0)
        spinner.setNumberOfLines(12)
        spinner.setLineLength(10)
        spinner.setLineWidth(5)
        spinner.setInnerRadius(10)
        spinner.setRevolutionsPerSecond(1)
        spinner.setColor(QColor(81, 4, 71))
        return spinner

    def plot(self, analysis_data):
        self.spinner.stop()

        if analysis_data.strategy_report is not None and analysis_data.benchmark_report is not None:
            strategy_data = analysis_data.strategy_report
            benchmark_data = analysis_data.benchmark_report

            self.strategy_returns[0].setText('{:.2f}%'.format(100 * strategy_data['total_return_pct']))
            self.strategy_returns[1].setText('{:.2f}'.format(100 * strategy_data['total_return']))
            self.strategy_returns[2].setText('{:.2f}%'.format(100 * strategy_data['cagr']))
            self.strategy_returns[3].setText('{:.2f}%'.format(100 * strategy_data['ytd']))

            self.benchmark_returns[0].setText('{:.2f}%'.format(100 * benchmark_data['total_return_pct']))
            self.benchmark_returns[1].setText('{:.2f}'.format(100 * benchmark_data['total_return']))
            self.benchmark_returns[2].setText('{:.2f}%'.format(100 * benchmark_data['cagr']))
            self.benchmark_returns[3].setText('{:.2f}%'.format(100 * benchmark_data['ytd']))

            for returns in itertools.chain(self.strategy_returns, self.benchmark_returns):
                if returns.text() != "-":
                    number = float(returns.text().replace("%", ""))
                    if number > 0:
                        returns.setStyleSheet('color: blue')
                    elif number < 0:
                        returns.setStyleSheet('color: red')
                    else:
                        returns.setStyleSheet('color: grey')

            if np.isnan(strategy_data['alpha']):
                strategy_data['alpha'] = 0
            if np.isnan(strategy_data['sharpe_ratio']):
                strategy_data['sharpe_ratio'] = 0

            self.strategy_ratios[0].setText('{:.2f}'.format(strategy_data['alpha']))
            self.strategy_ratios[1].setText('{:.2f}'.format(strategy_data['beta']))
            self.strategy_ratios[2].setText('{:.2f}'.format(strategy_data['sharpe_ratio']))
            # self.strategy_ratios[3].setText('{:.2f}'.format(strategy_data['win_ratio']))

            self.benchmark_ratios[0].setText('{:.2f}'.format(benchmark_data['alpha']))
            self.benchmark_ratios[1].setText('{:.2f}'.format(benchmark_data['beta']))
            self.benchmark_ratios[2].setText('{:.2f}'.format(benchmark_data['sharpe_ratio']))
            # self.benchmark_ratios[3].setText('{:.2f}'.format(benchmark_data['win_ratio']))

            self.strategy_volatility[0].setText('{:.2f}%'.format(100 * strategy_data['max_drawdown']))
            self.strategy_volatility[1].setText('{:.2f}'.format(strategy_data['std']))

            self.benchmark_volatility[0].setText('{:.2f}%'.format(100 * benchmark_data['max_drawdown']))
            self.benchmark_volatility[1].setText('{:.2f}'.format(benchmark_data['std']))


