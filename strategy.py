from zipline.utils.run_algo import run_algorithm
import threading
import sys
from analyzer.analyzer import Analyzer


class Strategy:

    def __init__(self, strategy_data):
        self.strategy_data = strategy_data
        self.analyzer = Analyzer(self)

    def initialize(self, context):
        self.strategy_data.get('initialize')(context)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.initialize()

    def handle_data(self, context, data):
        self.strategy_data.get('handle_data')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.handle_data(context)

    def analyze(self, context, data):
        self.strategy_data.get('analyze')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.finalize()

    def before_trading_start(self, context, data):
        self.strategy_data.get('before_trading_start')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.before_trading_start()

    def run_algorithm(self):
        if self.strategy_data.get('live_trading', False) is False:
            kwargs = {'start': self.strategy_data.get('start'),
                      'end': self.strategy_data.get('end'),
                      'initialize': self.initialize,
                      'handle_data': self.handle_data,
                      'analyze': self.analyze,
                      'before_trading_start': self.before_trading_start,
                      'bundle': 'quandl',
                      'capital_base': self.strategy_data.get('capital_base')}
        else:
            kwargs = {'start': self.strategy_data.get('start'),
                      'end': self.strategy_data.get('end'),
                      'initialize': self.initialize,
                      'handle_data': self.handle_data,
                      'analyze': self.analyze,
                      'before_trading_start': self.before_trading_start,
                      'bundle': 'quandl',
                      'capital_base': self.strategy_data.get('capital_base'),
                      'tws_uri': 'localhost:7497:1232',
                      'live_trading': True}

        run_algo_thread = threading.Thread(target=run_algorithm, kwargs=kwargs)
        run_algo_thread.start()

        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.show_plot()
            sys.exit(self.analyzer.app.exec_())