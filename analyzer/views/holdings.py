from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from analyzer.views.group_box import GroupConfigBoxWidget
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class HoldingsTab(AnalysisTab):

    def __init__(self, parent, analysis_data):
        super(QtWidgets.QWidget, self).__init__(parent)

        # self.resized.connect(self.resizeFunction)

        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()

        self.initUI()
        self.analysis_data = analysis_data

    def initUI(self):
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents.setFixedHeight(765)

        grid = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)

        group_widget = QtWidgets.QWidget()
        group_layout = QtWidgets.QVBoxLayout()

        self.holdingsTable = HoldingsTable()
        self.group_gbox = GroupConfigBoxWidget('Holdings', group_widget)
        group_vbox = QtWidgets.QVBoxLayout()

        group_vbox.addWidget(self.holdingsTable)
        group_vbox.setSpacing(0)
        self.group_gbox.setLayout(group_vbox)

        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(self.group_gbox)

        grid.addWidget(group_widget, 0, 0)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        outer_layout.addWidget(self.scrollArea)

        self.setLayout(outer_layout)

    def get_tab_name(self):
        return "Holdings"

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return "Showcase holdings for the day"

    def update_plot(self, analysis_data):
        if analysis_data is not None:
            self.analysis_data = analysis_data
            self.holdingsTable.update_data(self.analysis_data.holdings_data)

    def generate_report(self):
        pass

    # def resizeFunction(self):
    #     self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())
    #     # resize columns
    #     for col in range(0,4):
    # def resizeEvent(self, event):
    #     self.resized.emit()
    #     return super(WinnersLosersTab, self).resizeEvent(event)
    #
    # def resizeFunction(self):
    #     self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())
    #     # resize columns
    #     for col in range(0, 4):
    #         self.firstdistributionTable.setColumnWidth(col, int(self.scrollArea.size().width() / 7))
    #         self.seconddistributionTable.setColumnWidth(col, int(self.scrollArea.size().width() / 7))


class HoldingsTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(QtWidgets.QTableWidget, self).__init__()
        self.headers = ['Symbol', 'Name', 'Sector', 'Avg Price', 'Last Price',
                        '$ Daily Change', '% Daily Change', '$ Total Change', '% Total Change', '% Portfolio']
        self.setSortingEnabled(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # self.setRowCount(self.row_count)
        self.verticalHeader().hide()

        # set horizontal header
        for col in range(0, len(self.headers)):
            self.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(self.headers[col]))
            self.setColumnWidth(col, 70)

    def update_data(self, holdings_data):
        for i in range(0, len(holdings_data)):
            data = holdings_data.iloc[i]
            symbol = QtWidgets.QTableWidgetItem(data.symbol)
            symbol.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 0, symbol)

            name = QtWidgets.QTableWidgetItem(data.name)
            name.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 1, name)

            sector = QtWidgets.QTableWidgetItem(data.name)
            sector.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 2, sector)

            avg_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.avg_price))
            avg_price.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 3, avg_price)

            last_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.last_price))
            last_price.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 4, last_price)

            daily_change = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.daily_change))
            daily_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 5, daily_change)
            if data.daily_change > 0:
                self.item(i, 5).setForeground(QColor('blue'))
            elif data.daily_change < 0:
                self.item(i, 5).setForeground(QColor('red'))

            pct_daily_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_daily_change))
            pct_daily_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 6, pct_daily_change)
            if data.pct_daily_change > 0:
                self.item(i, 6).setForeground(QColor('blue'))
            elif data.daily_change < 0:
                self.item(i, 6).setForeground(QColor('red'))

            total_change = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.total_change))
            total_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 7, total_change)
            if data.daily_change > 0:
                self.item(i, 7).setForeground(QColor('blue'))
            elif data.daily_change < 0:
                self.item(i, 7).setForeground(QColor('red'))

            pct_total_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_total_change))
            pct_total_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 8, pct_total_change)
            if data.daily_change > 0:
                self.item(i, 8).setForeground(QColor('blue'))
            elif data.daily_change < 0:
                self.item(i, 8).setForeground(QColor('red'))

            pct_port = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_port))
            pct_port.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 9, pct_port)
