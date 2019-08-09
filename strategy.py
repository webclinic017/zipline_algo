from zipline.utils.run_algo import run_algorithm
import threading
import sys
from analyzer.analyzer import Analyzer
from email_service import EmailService

from sqlalchemy import create_engine
import datetime
import os
from pathlib import Path


class Strategy:

    def __init__(self, strategy_data):
        self.strategy_data = strategy_data
        self.analyzer = Analyzer(self)
        self.email_service = EmailService()

    def initialize(self, context):
        self.strategy_data.get('initialize')(context)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.initialize()
            self.email_service.initialize()

    def SendMessage(self, subject, message):
        if self.strategy_data.get('live_trading', False) is True:
            self.email_service.SendMessage(subject, message)

    def handle_data(self, context, data):
        self.strategy_data.get('handle_data')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.handle_data(context)

    def analyze(self, context, data):
        print("Analyse method got called")
        self.strategy_data.get('analyze')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.finalize()
        # if self.strategy_data.get('live_trading', False) is False:
        db_engine = create_engine('sqlite:///{}'.format(os.path.join(str(Path.home()), 'algodb.db')))
        sql = "INSERT INTO daily_portfolio VALUES ('{}', '{}', '{}');" \
            .format(context.datetime.date(), self.strategy_data.get('algo_name'), context.portfolio.portfolio_value)

        with db_engine.connect() as connection:
            try:
                connection.execute(sql)
            except Exception as e:
                print(e)

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