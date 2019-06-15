from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import gridspec
import pandas as pd
import calendar
import seaborn


class ComparisonTab(AnalysisTab):

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.calendar_plotter = CalendarPlotter(self)
        self.calendar_plotter.selected_period = 'quarterly'
        self.calendar_plotter.selected_metric = 'returns'

        grid = QtWidgets.QGridLayout()
        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)
        firstgroup_layout.addWidget(self.calendar_plotter)
        firstgroup_layout.setSpacing(0)
        firstgroup_layout.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(firstgroup_widget, 0, 0)
        self.setLayout(grid)

    def get_tab_name(self):
        return 'Comparison'

    def get_tab_description(self):
        return 'some description'

    def update_plot(self, analysis_data):
        self.calendar_plotter.plot(analysis_data)

    def generate_report(self):
        pass


class CalendarPlotter(FigureCanvas):

    def __init__(self, masterWindow):
        self.fig = Figure(figsize=(10, 7))
        gs = gridspec.GridSpec(1, 27)
        FigureCanvas.__init__(self, self.fig)

        self.heatmap_ax = self.fig.add_subplot(gs[0, 0:24], xticks=[], yticks=[])
        self.colorbar_ax = self.fig.add_subplot(gs[0, 26])

        self.setParent(masterWindow)
        self.analysis_data = None
        self.selected_period = None
        self.selected_metric = None

    def contextMenuEvent(self, a0: QtGui.QContextMenuEvent):
        contextManu = QtWidgets.QMenu(self)

        period_monthly = contextManu.addAction("Monthly")
        period_quarterly = contextManu.addAction("Quarterly")

        action = contextManu.exec_(self.mapToGlobal(a0.pos()))

        if action == period_monthly:
            self.selected_period = 'monthly'
        elif action == period_quarterly:
            self.selected_period = 'quarterly'

        self.plot(self.analysis_data)

    def plot(self, analysis_data=None):

        if analysis_data is not None:
            self.analysis_data = analysis_data

        if self.analysis_data is None or self.analysis_data.chart_data is None:
            return

        self.heatmap_ax.cla()

        data_series = self.get_data_series()

        if self.selected_period == 'monthly':
            self.heatmap_ax.yaxis.label.set_visible(False)

            heatmap_df = pd.DataFrame({'returns': data_series.values}, index=data_series.index)
            heatmap_df['Month'] = heatmap_df.index.month
            heatmap_df['Year'] = heatmap_df.index.year

            heatmap_returns = heatmap_df.pivot('Month', 'Year', 'returns')
            heatmap_returns.sort_index(level=0, ascending=True, inplace=True)
            heatmap_returns.rename(index=lambda x: calendar.month_abbr[x], inplace=True)
        elif self.selected_period == 'quarterly':
            self.heatmap_ax.yaxis.label.set_visible(True)

            heatmap_df = pd.DataFrame({'returns': data_series.values}, index=data_series.index)
            heatmap_df['Quarter'] = heatmap_df.index.month
            heatmap_df['Year'] = heatmap_df.index.year

            heatmap_returns = heatmap_df.pivot('Quarter', 'Year', 'returns')
            heatmap_returns.sort_index(level=0, ascending=True, inplace=True)

        graph = seaborn.heatmap(heatmap_returns, ax=self.heatmap_ax, fmt='.1%', cbar=True,
                                cbar_ax=self.colorbar_ax, center=0, robust=True,
                                )
        graph.xaxis.label.set_visible(False)
        graph.set_yticklabels(graph.get_yticklabels())

        self.draw()

    def get_data_series(self):
        if self.selected_period == 'monthly':
            sample_period = 'M'
        elif self.selected_period == 'quarterly':
            sample_period = 'Q'

        self.analysis_data.chart_data.index = pd.to_datetime(self.analysis_data.chart_data.index)

        if self.selected_metric == 'returns':
            return ((self.analysis_data.chart_data.returns + 1).resample(sample_period).prod() - 1)