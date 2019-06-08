from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from analyzer.views.overview import OverviewTab
from analyzer.views.performance import PerformanceTab
from analyzer.views.holdings import HoldingsTab
from analyzer.analysis_data import AnalysisData


class AnalyzerWindow(QtWidgets.QMainWindow):
    all_tabs_dict = {}
    updateSignal = QtCore.pyqtSignal(AnalysisData)

    def __init__(self, analysis_data, app):
        self.app = app
        self.analysis_data = analysis_data
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle(self.analysis_data.info_data['algo_name'])

        plt.style.use('seaborn-bright')
        self.setMinimumHeight(720)
        self.setMinimumWidth(960)

        overview_tab = OverviewTab(self, self.analysis_data)
        performance_tab = PerformanceTab(self, self.analysis_data)
        holdings_tab = HoldingsTab(self)

        self.all_tabs_dict[overview_tab.get_tab_name()] = overview_tab
        self.all_tabs_dict[performance_tab.get_tab_name()] = performance_tab
        self.all_tabs_dict[holdings_tab.get_tab_name()] = holdings_tab

        self.main_widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.setSpacing(10)

        self.tab_widget = TabWidget(self)

        layout.addWidget(self.tab_widget)

        file_menu = QtWidgets.QMenu('&File', self)

        self.menuBar().addMenu(file_menu)

        self.main_widget.setFocus()
        # self.setStyleSheet("color: black; background-color: white")
        self.setCentralWidget(self.main_widget)

        self.add_tab(overview_tab.get_tab_name())
        self.add_tab(performance_tab.get_tab_name())
        self.add_tab(holdings_tab.get_tab_name())

        # connect to event
        self.updateSignal.connect(self.update_plot)

    @QtCore.pyqtSlot(AnalysisData)
    def update_plot(self, analysis_data):
        if analysis_data is not None:
            self.analysis_data = analysis_data

        try:
            self.tab_widget.tabs.currentWidget().update_plot(self.analysis_data)
        except Exception as e:
            print(e)

    def add_tab(self, name):
        tab_object = self.all_tabs_dict[name]
        if tab_object is not None:
            tab_index = self.tab_widget.tabs.addTab(tab_object, name)
            self.tab_widget.tabs.setCurrentIndex(tab_index)


class TabWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setAcceptDrops(False)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
