from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from PyQt5.QtGui import QColor


class OverviewTab(AnalysisTab):
    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.plotter = OverviewWidget(self)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.plotter)
        self.setLayout(self.layout)

    def get_tab_name(self):
        return "Overview"

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return "Some description"

    def update_plot(self):
        self.plotter.plot()

    def generate_report(self):
        pass


class OverviewWidget(QtWidgets.QTableWidget):
    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        # configure layout

    def plot(self):
        pass