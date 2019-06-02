from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from analyzer.views.overview import OverviewTab


class AnalyzerWindow(QtWidgets.QMainWindow):
    all_tabs_dict = {}

    def __init__(self, app):
        self.app = app
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Some title')

        plt.style.use('seaborn-bright')
        self.setMinimumHeight(720)
        self.setMinimumWidth(960)

        overview_tab = OverviewTab(self)

        self.all_tabs_dict[overview_tab.get_tab_name()] = overview_tab

        self.main_widget = QtWidgets.QWidget(self)

        layout = QtWidgets.QVBoxLayout(self.main_widget)
        layout.setSpacing(10)


        self.tab_widget = TabWidget(self)

        layout.addWidget(self.tab_widget)

        file_menu = QtWidgets.QMenu('&File', self)

        self.menuBar().addMenu(file_menu)

        self.main_widget.setFocus()
        self.setStyleSheet("color: black; background-color: white")
        self.setCentralWidget(self.main_widget)

        self.add_tab(overview_tab.get_tab_name())

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
