import matplotlib.pyplot as plt
import os
from ote import config
from ote.analyzer.exporter import PdfGenerator
from ote.analyzer.views.analysis_data import AnalysisData
from ote.analyzer.views.drawdown import DrawdownTab
from ote.analyzer.views.overview import OverviewTab
from ote.analyzer.views.returns import ReturnsTab
from ote.analyzer.views.messages import MessagesTab
from ote.analyzer.views.period_wise import PeriodWiseTab
from ote.analyzer.views.performance import PerformanceTab
from ote.analyzer.views.regression import RegressionTab
from ote.analyzer.views.status import StatusWidget
from ote.analyzer.views.view_selector import ViewSelector
from ote.analyzer.views.winners_losers import WinnersLosersTab
from ote.analyzer.views.events import EvetnsTab
from ote.analyzer.views.roundtrips import RoundTripsTab
from ote.utils import results_path
import pickle
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtCore import Qt
import sys
import traceback


class AnalyzerWindow(QtWidgets.QMainWindow):
    all_tabs_dict = {}

    updateSignal = QtCore.pyqtSignal(AnalysisData)
    viewSelectorSignal = QtCore.pyqtSignal(str)

    def __init__(self, analysis_data, strategyApp):
        self.analysis_data = analysis_data
        self.strategyApp = strategyApp

        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.set_window_title(analysis_data.info_data['algo_name'], analysis_data.info_data['backtest_name'])

        matplot_style = config.get(name='plot.style', default_value='seaborn-bright')
        if matplot_style in plt.style.available:
            plt.style.use(matplot_style)
        self.setMinimumHeight(720)
        self.setMinimumWidth(960)

        overview_tab = OverviewTab(self, self.analysis_data)
        regression_tab = RegressionTab(self)
        drawdownTab = DrawdownTab(self)
        period_tab = PeriodWiseTab(self)
        returns_tab = ReturnsTab(self, analysis_data)
        messages_tab = MessagesTab(self)
        self.performance_tab = PerformanceTab(self)
        win_lose_tab = WinnersLosersTab(self)
        events_tab = EvetnsTab(self)
        roundtrips_tab = RoundTripsTab(self)

        self.all_tabs_dict[regression_tab.get_tab_name()] = regression_tab
        self.all_tabs_dict[drawdownTab.get_tab_name()] = drawdownTab
        self.all_tabs_dict[overview_tab.get_tab_name()] = overview_tab
        self.all_tabs_dict[period_tab.get_tab_name()] = period_tab
        self.all_tabs_dict[returns_tab.get_tab_name()] = returns_tab
        self.all_tabs_dict[messages_tab.get_tab_name()] = messages_tab
        self.all_tabs_dict[self.performance_tab.get_tab_name()] = self.performance_tab
        self.all_tabs_dict[win_lose_tab.get_tab_name()] = win_lose_tab
        self.all_tabs_dict[events_tab.get_tab_name()] = events_tab
        self.all_tabs_dict[roundtrips_tab.get_tab_name()] = roundtrips_tab

        self.main_widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.setSpacing(10)

        self.tab_widget = TabWidget(self)
        self.tab_widget.tabs.currentChanged.connect(self.tab_current_changed)
        self.tab_widget.tabs.tabBarDoubleClicked.connect(self.tab_close_requested)
        layout.addWidget(self.tab_widget)

        self.status_widget = StatusWidget(self)
        self.status_widget.setContentsMargins(-1, -12, -1, -8)
        layout.addWidget(self.status_widget)

        # create corner widget
        tab_button = self.create_corner_widget()
        self.tab_widget.tabs.setCornerWidget(tab_button, corner=Qt.TopRightCorner)
        tab_button.clicked.connect(self.open_view_selector)

        file_menu = QtWidgets.QMenu('&File', self)

        # open result action
        self.open_result_action = QtWidgets.QAction('&Open', self)
        self.open_result_action.triggered.connect(self.open_result)
        self.open_result_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_O)


        # file_menu.addAction(self.run_algorithm_action)
        file_menu.addAction(self.open_result_action)
        file_menu.addSeparator()
        file_menu.addAction('E&xit', self.fileQuit, QtCore.Qt.CTRL + QtCore.Qt.Key_X)

        export_menu = QtWidgets.QMenu('&Export', self)
        # generate pdf action
        self.generate_pdf_action = QtWidgets.QAction('&PDF Export', self)
        self.generate_pdf_action.triggered.connect(self.generate_pdf)
        self.generate_pdf_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_P)
        self.generate_pdf_action.setVisible(True)

        export_menu.addAction('&Chart CSV', self.export_chart_data, QtCore.Qt.CTRL + QtCore.Qt.Key_C)
        export_menu.addAction('E&vents CSV', self.export_events_data, QtCore.Qt.CTRL + QtCore.Qt.Key_V)
        export_menu.addAction('&Roundtrip CSV', self.export_roundtrip_data, QtCore.Qt.CTRL + QtCore.Qt.Key_R)
        export_menu.addAction('&Transactions CSV', self.export_orders_data, QtCore.Qt.CTRL + QtCore.Qt.Key_T)
        export_menu.addSeparator()
        export_menu.addAction(self.generate_pdf_action)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(export_menu)

        self.main_widget.setFocus()
        self.setStyleSheet("color: black; background-color: white")
        self.setCentralWidget(self.main_widget)

        # finally add overview & performance tabs by default
        self.add_tab(overview_tab.get_tab_name())
        self.add_tab(self.performance_tab.get_tab_name())

        # connect to our event
        self.updateSignal.connect(self.update_plot)
        self.viewSelectorSignal.connect(self.add_tab)

    def open_result(self):
        try:
            options = QtWidgets.QFileDialog.Options()
            fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                      "Pickle Files (*.pkl)", options=options)

            if fileName:
                # self.generate_pdf_action.setVisible(True)
                with open(fileName, 'rb') as f:
                    a = pickle.load(f)

                    self.aw = self.open_new_analyzer_window(a)
        except:
            e = sys.exc_info()[0]
            print(e)
            traceback.print_exc()

    def open_view_selector(self):
        self.view_selector = ViewSelector(self)

    def set_window_title(self, algo_name, backtest_name):
        title = algo_name + (
            ' [' + backtest_name + ']' if backtest_name is not None else '') + ' - OTE Backtest'
        self.setWindowTitle(title)

    def create_corner_widget(self):
        tabButton = QToolButton(self)
        tabButton.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'resources', "icons8-plus-math-24.png")))
        tabButton.setStyleSheet('QToolButton { border: none; }')
        font = tabButton.font()
        font.setBold(True)
        tabButton.setFont(font)

        return tabButton

    @QtCore.pyqtSlot(AnalysisData)
    def update_plot(self, analysis_data):
        if analysis_data is not None:
            self.analysis_data = analysis_data

        try:
            self.tab_widget.tabs.currentWidget().update_plot(self.analysis_data)
            self.status_widget.plotter.plot(self.analysis_data)
        except:
            e = sys.exc_info()[0]
            print(e)
            traceback.print_exc()

    @QtCore.pyqtSlot(AnalysisData)
    def open_new_analyzer_window(self, a):
        if a is not None:
            try:
                aw = AnalyzerWindow(a, self.strategyApp)
                # aw.set_window_title(analysis_data.info_data['algo_name'],  analysis_data.info_data['backtest_name'])
                aw.show()
                aw.updateSignal.emit(a)

                return aw
            except:
                e = sys.exc_info()[0]
                print(e)
                traceback.print_exc()

    def generate_pdf(self):
        pdf_generator = PdfGenerator(tabs=self.all_tabs_dict, analysis_data=self.analysis_data, app=self.strategyApp)
        pdf_generator.generate()

    def export_chart_data(self):
        # get chart_data
        chart_data = self.analysis_data.chart_data.reset_index()

        # dump to csv
        chart_data.to_csv(os.path.join(results_path, 'data_chart.csv'), header=True, index=False)

    def export_roundtrip_data(self):
        roundtrip_df = self.analysis_data.roundtrip_data.reset_index()

        # get Symbol column from instrument and drop instrument column after
        roundtrip_df['symbol'] = roundtrip_df['instrument'].apply(lambda x: x.won_symbol)
        roundtrip_df.drop('instrument', axis=1, inplace=True)

        if not roundtrip_df.empty:
            # dump to csv
            roundtrip_df.to_csv(os.path.join(results_path, 'data_roundtrip.csv'), header=True, index=False)

    def export_events_data(self):
        event_track_df = self.analysis_data.event_tracks.reset_index()
        if not event_track_df.empty:
            # dump to csv
            event_track_df['symbol'] = event_track_df['instrument'].apply(lambda x: x.won_symbol)
            event_track_df.drop('instrument', axis=1, inplace=True)
            event_track_df.to_csv(os.path.join(results_path, 'data_event_track.csv'), header=True, index=False)

        event_stats_df = self.analysis_data.event_stats.reset_index()
        if not event_track_df.empty:
            # dump to csv
            event_stats_df.to_csv(os.path.join(results_path, 'data_event_stats.csv'), header=True, index=False)

    def export_orders_data(self):
        orders_df = self.analysis_data.orders_data.reset_index()
        if not orders_df.empty:
            orders_df.to_csv(os.path.join(results_path, 'data_transactions.csv'), header=True, index=False)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def tab_close_requested(self, tab):
        selected_tab = self.tab_widget.tabs.widget(tab)
        # dont close if it is Overview Tab
        if selected_tab.get_tab_name() == 'Overview':
            return
        # selected_tab_menu = selected_tab.get_tab_menu()
        # if selected_tab_menu is not None:
        #    selected_tab_menu.menuAction().setVisible(False)
        self.tab_widget.tabs.removeTab(tab)

    def tab_current_changed(self, tab):
        # self.tab_widget.tabs.currentWidget().update_plot(self.chart_data, self.report_data, self.strategy)
        if self.analysis_data is not None:
            try:
                self.updateSignal.emit(self.analysis_data)
            except:
                e = sys.exc_info()[0]
                print(e)
                traceback.print_exc()
        return

    def make_add_tab(self, name):
        def add_tab():
            self.add_tab(name)
        return add_tab

    def add_tab(self, name):
        # add tabs
        tab_object = self.all_tabs_dict[name]
        if tab_object is not None:
            tab_index = self.tab_widget.tabs.addTab(tab_object, name)
            self.tab_widget.tabs.setCurrentIndex(tab_index)


class TabWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Initialize tab screen
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setAcceptDrops(False)
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)