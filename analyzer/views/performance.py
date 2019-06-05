from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import gridspec
import empyrical

class PerformanceTab(AnalysisTab):

    def __init__(self, parent, analysis_data):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.plotter = Plotter(self)
        self.analysis_data = analysis_data

        grid = QtWidgets.QGridLayout()
        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)
        firstgroup_layout.addWidget(self.plotter)
        firstgroup_layout.setSpacing(0)
        firstgroup_layout.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(firstgroup_widget, 0, 0)
        self.setLayout(grid)

    def get_tab_name(self):
        return 'Performance'

    def get_tab_description(self):
        return 'some description'

    def update_plot(self, analysis_data):
        self.plotter.plot(analysis_data)

    def generate_report(self):
        pass

class Plotter(FigureCanvas):

    def __init__(self, masterWindow):
        self.fig = Figure(figsize=(10, 7))
        gs = gridspec.GridSpec(1, 1)
        self.returns_ax = self.fig.add_subplot(gs[0, 0], xticks=[], yticks=[])
        FigureCanvas.__init__(self, self.fig)
        self.setParent(masterWindow)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        FigureCanvas.updateGeometry(self)

    def plot(self, analysis_data=None):
        if analysis_data is not None:
            self.analysis_data = analysis_data

        if self.analysis_data is None or self.analysis_data.chart_data is None:
            return

        self.returns_ax.cla()
        self.portfolio_total_returns = empyrical.cum_returns(self.analysis_data.chart_data.returns) * 100
        self.benchmark_total_returns = empyrical.cum_returns(self.analysis_data.chart_data.benchmark_returns) * 100

        self.returns_ax.plot(self.portfolio_total_returns)
        self.returns_ax.plot(self.benchmark_total_returns)
        self.returns_ax.legend(['Strategy', 'SPY'], loc='upper left')
        self.returns_ax.grid(True)
        self.returns_ax.set_ylabel('Return')
        self.draw()
