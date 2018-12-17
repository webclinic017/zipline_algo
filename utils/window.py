import matplotlib.pyplot as plt
import os
from utils.analysis_data import AnalysisData
from utils.views.drawdown import DrawdownTab
from utils.views.overview import OverviewTab
from utils.views.performance import PerformanceTab
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

        matplot_style = 'seaborn-bright'
        if matplot_style in plt.style.available:
            plt.style.use(matplot_style)
        self.setMinimumHeight(720)
        self.setMinimumWidth(960)

        overview_tab = OverviewTab(self, self.analysis_data)
        drawdownTab = DrawdownTab(self)
        self.performance_tab = PerformanceTab(self)

        self.all_tabs_dict[drawdownTab.get_tab_name()] = drawdownTab
        self.all_tabs_dict[overview_tab.get_tab_name()] = overview_tab
        self.all_tabs_dict[self.performance_tab.get_tab_name()] = self.performance_tab

        self.main_widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.setSpacing(10)

        self.tab_widget = TabWidget(self)
        self.tab_widget.tabs.currentChanged.connect(self.tab_current_changed)
        self.tab_widget.tabs.tabBarDoubleClicked.connect(self.tab_close_requested)
        layout.addWidget(self.tab_widget)

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
