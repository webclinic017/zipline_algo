from PyQt5 import QtWidgets
from analyzer.views.main import AnalyzerWindow
import sys
import pandas as pd
from analyzer.analysis_data import AnalysisData


class Analyzer:
    def __init__(self, strategy):
        self.app = QtWidgets.QApplication(sys.argv)
        self.daily_data_df = pd.DataFrame(columns=['date', 'net'])
        self.daily_data_df.set_index('date', inplace=True)


        self.analysis_data = AnalysisData()
        self.strategy = strategy

        self.analysis_data.info_data['algo_name'] = self.strategy.strategy_data.get('algo_name')

        self.aw = AnalyzerWindow(self.analysis_data, self.app)

    def initialize(self):
        pass

    def before_trading_start(self):
        pass

    def handle_data(self):
        self.aw.updateSignal.emit(self.analysis_data)

    def after_trading_end(self):
        pass

    def finalize(self):
        pass

    def show_plot(self):
        self.aw.show()
