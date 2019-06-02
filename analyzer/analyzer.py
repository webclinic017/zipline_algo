from PyQt5 import QtWidgets
from analyzer.views.main import AnalyzerWindow
import sys
import pandas as pd


class Analyzer:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.daily_data_df = pd.DataFrame(columns=['date', 'net'])
        self.daily_data_df.set_index('date', inplace=True)

        self.aw = AnalyzerWindow(self.app)

    def initialize(self):
        pass

    def before_trading_start(self):
        pass

    def handle_data(self):
        pass

    def finalize(self):
        pass

    def show_plot(self):
        self.aw.show()