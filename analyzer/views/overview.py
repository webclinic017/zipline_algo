from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from analyzer.views.spinnerwidget import QtWaitingSpinner
from analyzer.views.group_box import GroupConfigBoxWidget
from PyQt5.QtGui import QColor


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
        pass


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

        self.strategy_returns = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self),
                                 QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self)]

        self.benchmark_returns = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self),
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
            # QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data['benchmark_symbol']
            #                  + "</font></strong>", self), 2, 0)
        QtWidgets.QLabel("<font color='#666666'><strong>" + "temp sym"
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
        # ratio_grid.addWidget(
        #     QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data[
        #         'benchmark_symbol'] + "</font></strong>", self), 2, 0)
        ratio_grid.addWidget(
            QtWidgets.QLabel("<font color='#666666'><strong>" + "temp sym" + "</font></strong>", self), 2, 0)

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

        self.strategy_volatility = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self)]

        self.benchmark_volatility = [QtWidgets.QLabel('0%', self), QtWidgets.QLabel('0%', self)]

        for col, label, strategy_return, benchmark_return in zip(range(1, len(self.volatility_labels) + 1),
                                                                 self.volatility_labels,
                                                                 self.strategy_volatility,
                                                                 self.benchmark_volatility):
            volatility_grid.addWidget(
                QtWidgets.QLabel("<font color='#666666'><strong>" + label + "</font></strong>"),
                0, col)
            volatility_grid.addWidget(strategy_return, 1, col)
            volatility_grid.addWidget(benchmark_return, 2, col)

        volatility_grid.addWidget(QtWidgets.QLabel("<font color='#666666'><strong>Strategy</font></strong>", self),
                                  1, 0)
        # volatility_grid.addWidget(
        #     QtWidgets.QLabel("<font color='#666666'><strong>" + self.analysis_data.info_data[
        #         'benchmark_symbol'] + "</font></strong>", self),
        #     2, 0)
        volatility_grid.addWidget(
            QtWidgets.QLabel("<font color='#666666'><strong>" + "temp sym" + "</font></strong>", self),
            2, 0)

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
        self.test_label.setText(analysis_data.info_data.get('algo_name'))
