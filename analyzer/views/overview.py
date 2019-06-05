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

    def update_plot(self, analysis_data):
        self.plotter.plot(analysis_data)

    def generate_report(self):
        pass


class OverviewWidget(QtWidgets.QTableWidget):
    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        # configure layout
        self.test_label = QtWidgets.QLabel('Testing', self)

    def plot(self, analysis_data):
        self.test_label.setText(analysis_data.info_data.get('algo_name'))
