from analyzer.views.analysistab import AnalysisTab
from PyQt5 import QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class TransactionsTab(AnalysisTab):
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

        self.transactionstable = TransactionsTable()
        firstgroup_layout.addWidget(self.transactionstable)

        grid.addWidget(firstgroup_widget, 1, 0, 1, 2)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        outer_layout.addWidget(self.scrollArea)

        self.setLayout(outer_layout)

    def get_tab_name(self):
        return "Transactions"

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return "Showcase transactions for the day"

    def update_plot(self, analysis_data):
        if analysis_data is not None:
            self.analysis_data = analysis_data

        if self.analysis_data is not None and self.analysis_data.transactions_data is not None:
            self.transactionstable.update_data(self.analysis_data.transactions_data)

    def generate_report(self):
        pass

    def resizeEvent(self, event):
        self.resized.emit()
        return super(TransactionsTab, self).resizeEvent(event)

    def resizeFunction(self):
        self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())
        # resize column
        for col in range(0, 5):
            self.transactionstable.setColumnWidth(col, int(self.scrollArea.size().width() / 6))


class TransactionsTable(QtWidgets.QTableWidget):
    row_count = 20

    def __init__(self):
        super(QtWidgets.QTableWidget, self).__init__()
        self.column_headers = ['Count', 'Date', 'Symbol', 'Name', 'Transaction Type', 'Quantity', 'Avg Price']
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setRowCount(self.row_count)
        self.verticalHeader().hide()

        self.setColumnCount(len(self.column_headers))

        # set horizontal header
        for col in range(0, len(self.column_headers)):
            self.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(self.column_headers[col]))
            self.setColumnWidth(col, 180)

    def update_data(self, row_data_df):
        if not row_data_df.empty:
            self.setRowCount(row_data_df.shape[0])
            for i in range(0, len(row_data_df)):
                data = row_data_df.iloc[i]

                counter = QtWidgets.QTableWidgetItem(str(data.counter))
                counter.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 0, counter)

                date = QtWidgets.QTableWidgetItem(str(data.date))
                date.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 1, date)

                symbol = QtWidgets.QTableWidgetItem(data.symbol)
                symbol.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 2, symbol)

                company_name = QtWidgets.QTableWidgetItem(data.company_name)
                company_name.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 3, company_name)

                tran_type = QtWidgets.QTableWidgetItem(data.transaction_type)
                tran_type.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 4, tran_type)

                quantity = QtWidgets.QTableWidgetItem(str(data.quantity))
                quantity.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 5, quantity)

                avg_price = QtWidgets.QTableWidgetItem('{:.2f}'.format(data.avg_price))
                avg_price.setTextAlignment(Qt.AlignRight)
                self.setItem(i, 6, avg_price)
        else:
            self.setRowCount(0)