from zipline.utils.run_algo import run_algorithm
import threading
import sys
from analyzer.analyzer import Analyzer

class Strategy():

    def __init__(self, strategy_data):
        self.analyzer = Analyzer()
        self.strategy_data = strategy_data

    def initialize(self, context):
        self.strategy_data.get('initialize')(context)
        self.analyzer.initialize()

    def handle_data(self, context, data):
        self.strategy_data.get('handle_data')(context, data)
        self.analyzer.handle_data()

    def analyze(self, context, data):
        self.strategy_data.get('analyze')(context, data)
        self.analyzer.finalize()

    def before_trading_start(self, context, data):
        self.strategy_data.get('before_trading_start')(context, data)
        self.analyzer.before_trading_start()

    def run_algorithm(self):
        kwargs = {'start': self.strategy_data.get('start'),
                  'end': self.strategy_data.get('end'),
                  'initialize': self.initialize,
                  'handle_data': self.handle_data,
                  'analyze': self.analyze,
                  'before_trading_start': self.before_trading_start,
                  'bundle': 'quandl',
                  'capital_base': self.strategy_data.get('capital_base')}
        run_algo_thread = threading.Thread(target=run_algorithm, kwargs=kwargs)
        run_algo_thread.start()

        self.analyzer.show_plot()
        sys.exit(self.analyzer.app.exec_())