from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from analyzer.views.group_box import GroupConfigBoxWidget
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class HoldingsTab(AnalysisTab):
    resized = pyqtSignal()

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.resized.connect(self.resizeFunction)

        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()

        self.initUI(parent)
        self.analysis_data = None

    def initUI(self, parent):
        # scroll
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents.setFixedHeight(765)

        # configure layout
        grid = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)

        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)

        self.holdingstable = HoldingsTable()
        self.holdingstable.filter_type = self.holdingstable.filter_type_top
        self.firstgroup_gbox = GroupConfigBoxWidget('Holdings: ', firstgroup_widget)
        firstgroup_vbox = QtWidgets.QVBoxLayout()

        firstgroup_vbox.addWidget(self.holdingstable)
        firstgroup_vbox.setSpacing(0)
        self.firstgroup_gbox.setLayout(firstgroup_vbox)

        firstgroup_layout.setContentsMargins(0, 0, 0, 0)
        firstgroup_layout.addWidget(self.firstgroup_gbox)

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
        report = {'winners': self.generate_table('winners'), 'losers': self.generate_table('losers')}

        row_data = []
        for row_id in range(0, 4):
            col_data = [self.winners_stats_column_headers[row_id],
                        self.winners_stats_column_values[row_id].text()]
            row_data.append(col_data)
        report['stats'] = row_data
        return report

    def generate_table(self, win_or_lose):
        if win_or_lose == 'winners':
            table = self.firstdistributionTable
            column_headers = table.winners_column_headers
        else:
            table = self.seconddistributionTable
            column_headers = table.losers_column_headers

        row_data = []
        # Add Headers only if table is not empty
        if table.item(0, 0) is not None:
            row_data = [column_headers]
            for row_id in range(0, 10):
                # If 'In Date' is null, break
                if table.item(row_id, 0) is None:
                    break
                col_data = [table.item(row_id, x).text()
                            if table.item(row_id, x) is not None else ''
                            for x, y in enumerate(column_headers)]
                row_data.append(col_data)

        return row_data

    def resizeEvent(self, event):
        self.resized.emit()
        return super(HoldingsTab, self).resizeEvent(event)

    def resizeFunction(self):
        self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())
        # resize columns
        for col in range(0, 9):
            self.holdingstable.setColumnWidth(col, int(self.scrollArea.size().width() / 11))


class HoldingsTable(QtWidgets.QTableWidget):
    filter_type_top = 'Return (Best)'

    filter_type = filter_type_top
    row_count = 50

    def __init__(self):
        super(QtWidgets.QTableWidget, self).__init__()
        self.column_headers = ['Symbol', 'Name', 'Sector', 'Avg Price', 'Last Price',
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

    def update_data(self, holdings_df):
            if not holdings_df.empty:
                self.update_row(holdings_df)

    def update_row(self, row_data_df):
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

            avg_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.avg_price))
            avg_price.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 3, avg_price)

            last_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.last_price))
            last_price.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 4, last_price)

            daily_change = QtWidgets.QTableWidgetItem('{:.2f}$'.format(data.daily_change))
            daily_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 5, daily_change)

            pct_daily_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_daily_change))
            pct_daily_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 6, pct_daily_change)
            if data.pct_daily_change > 0:
                self.item(i, 6).setForeground(QColor('blue'))
            elif data.pct_daily_change < 0:
                self.item(i, 6).setForeground(QColor('red'))

            total_change = QtWidgets.QTableWidgetItem('{:.2f}$'.format(data.total_change))
            total_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 7, total_change)

            pct_total_change = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_total_change))
            pct_total_change.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 8, pct_total_change)
            if data.pct_total_change > 0:
                self.item(i, 8).setForeground(QColor('blue'))
            elif data.pct_total_change < 0:
                self.item(i, 8).setForeground(QColor('red'))

            pct_port = QtWidgets.QTableWidgetItem('{:.2f}%'.format(data.pct_port))
            pct_port.setTextAlignment(Qt.AlignRight)
            self.setItem(i, 9, pct_port)


class NumericItem(QtWidgets.QTableWidgetItem):
    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)
