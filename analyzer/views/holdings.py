from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class HoldingsTab(AnalysisTab):
    resized = pyqtSignal()

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.resized.connect(self.resizeFunction)

        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()

        self.initUI()
        self.analysis_data = None

    def initUI(self):
        # scroll
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents.setFixedHeight(620)

        # configure layout
        grid = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)

        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)
        firstgroup_layout.setContentsMargins(5, 5, 5, 5)

        self.holdingstable = HoldingsTable()
        firstgroup_layout.addWidget(self.holdingstable)

        grid.addWidget(firstgroup_widget, 1, 0, 1, 2)

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

        if self.analysis_data is not None and self.analysis_data.holdings_data is not None:
            self.holdingstable.update_data(self.analysis_data.holdings_data)

    def generate_report(self):
        pass

    def resizeEvent(self, event):
        self.resized.emit()
        return super(HoldingsTab, self).resizeEvent(event)

    def resizeFunction(self):
        self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())
        # resize column
        for col in range(0, 10):
            self.holdingstable.setColumnWidth(col, int(self.scrollArea.size().width() / 11))


class HoldingsTable(QtWidgets.QTableWidget):
    row_count = 20

    def __init__(self):
        super(QtWidgets.QTableWidget, self).__init__()
        self.column_headers = ['Symbol', 'Name', 'Sector', 'Quantity', 'Avg Price', 'Last Price',
                               '$ Daily Change', '% Daily Change', '$ Total Change', '% Total Change', '% Portfolio']
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setRowCount(self.row_count)
        self.verticalHeader().hide()

        self.setColumnCount(len(self.column_headers))

        # set horizontal header
        for col in range(0, len(self.column_headers)):
            self.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(self.column_headers[col]))
            self.setColumnWidth(col, 140)

    def update_data(self, row_data_df):
        if not row_data_df.empty:
            for i in range(0, len(row_data_df)):
                data = row_data_df.iloc[i]
                symbol = QtWidgets.QTableWidgetItem(data.symbol)
                symbol.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 0, symbol)

                name = QtWidgets.QTableWidgetItem(data.name)
                name.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 1, name)

                sector = QtWidgets.QTableWidgetItem(data.sector)
                sector.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 2, sector)

                quantity = QtWidgets.QTableWidgetItem(str(int(data.quantity)))
                quantity.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 3, quantity)

                avg_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.avg_price))
                avg_price.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 4, avg_price)

                last_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.last_price))
                last_price.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 5, last_price)

                daily_change = QtWidgets.QTableWidgetItem('{:.2f}$'.format(data.daily_change))
                daily_change.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 6, daily_change)

                pct_daily_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_daily_change))
                pct_daily_change.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 7, pct_daily_change)
                if data.pct_daily_change > 0:
                    self.item(i, 7).setForeground(QColor('blue'))
                elif data.pct_daily_change < 0:
                    self.item(i, 7).setForeground(QColor('red'))

                total_change = QtWidgets.QTableWidgetItem('{:.2f}$'.format(data.total_change))
                total_change.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 8, total_change)

                pct_total_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_total_change))
                pct_total_change.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 9, pct_total_change)
                if data.pct_total_change > 0:
                    self.item(i, 9).setForeground(QColor('blue'))
                elif data.pct_total_change < 0:
                    self.item(i, 9).setForeground(QColor('red'))

                pct_port = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_port))
                pct_port.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 10, pct_port)
