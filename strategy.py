from zipline.utils.run_algo import run_algorithm
import threading
import sys
from analyzer.analyzer import Analyzer
from email_service import EmailService
import pandas as pd
from sqlalchemy import create_engine
import os
from pathlib import Path


class Strategy:

    def __init__(self, strategy_data):
        self.strategy_data = strategy_data
        self.analyzer = Analyzer(self)
        self.email_service = EmailService()

    def initialize(self, context):
        context.algo_id = self.strategy_data.get('algo_id')
        context.live_trading = self.strategy_data.get('live_trading')
        self.strategy_data.get('initialize')(context)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.initialize()
        else:
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
        else:
            algo_id = self.strategy_data.get('algo_id')
            db_engine = create_engine('sqlite:///{}'.format(os.path.join(str(Path.home()), 'algodb.db')))
            prev_date_sql = "select date from prev_run_date where algo_id={}".format(algo_id)
            prev_run_date = pd.read_sql(prev_date_sql, db_engine)['date'][0]
            run_date = str(context.datetime.date())

            prev_pos_sql = "select holding_name, quantity, buy_price, last_price from daily_holdings " \
                           "where algo_id={} and date='{}'".format(algo_id, prev_run_date)
            prev_pos = pd.read_sql(prev_pos_sql, db_engine)
            if prev_pos.empty:
                prev_pos_list = []
            else:
                prev_pos_list = list(prev_pos['holding_name'])
            prev_pos.set_index('holding_name', inplace=True)
            curr_positions = context.portfolio.positions.values()
            stock_email_columns = ['Holding', 'Shares', 'Buy Price', 'Yest Price', 'Current Price',
                                   'Dollar Gain Today', 'Pct Gain Today', 'Dollar Gain Net', 'Pct Gain Net',
                                   'Market Value']
            stock_email = pd.DataFrame(columns=stock_email_columns)
            sold_list = []
            for position in list(curr_positions):
                if position.sid.symbol in prev_pos_list:
                    if position.amount == 0:
                        sold_list.append(position)
                        continue
                    prev_stock_pos = prev_pos.loc[position.sid.symbol]
                    gain_today = position.last_sale_price - prev_stock_pos['last_price']
                    pct_gain_today = str(round((gain_today / prev_stock_pos['last_price']) * 100, 4)) + ' %'
                    gain_total = position.last_sale_price - position.cost_basis
                    pct_gain_total = str(round((gain_total / position.cost_basis) * 100, 4)) + ' %'
                    stock_email.loc[position.asset] = [position.asset.symbol, position.amount, round(position.cost_basis, 4),
                                          prev_stock_pos['last_price'], position.last_sale_price,
                                          gain_today, pct_gain_today, gain_total, pct_gain_total,
                                          position.amount * position.last_sale_price]
                else:
                    stock_email.loc[position.asset] = [position.asset.symbol, position.amount, round(position.cost_basis, 4),
                                            '-', position.last_sale_price,
                                            '-', '-', '-', '-',
                                            position.amount * position.last_sale_price]

            portfolio = context.portfolio
            # stock_email = stock_email.join(pd.DataFrame(portfolio.current_portfolio_weights, columns=['Weightage']))
            # stock_email['Weightage'] = round(stock_email['Weightage'] * 100, 4).astype(str) + ' %'
            port_email = pd.Series([round(portfolio.portfolio_value, 4),
                                    round(portfolio.pnl, 4),
                                    str(round(portfolio.pnl/(portfolio.portfolio_value-portfolio.pnl), 4))+' %',
                                    round(portfolio.cash, 4), round(portfolio.positions_value, 4)],
                                   index=['Portfolio Value', 'Net Gain', 'Percent Net Gain',
                                          'Cash Value', 'Position Value'])

            message = "<p><h3>Holdings Summary</h3></p>" + stock_email.to_html(index=False) \
                      + "<p><h3>Portfolio Summary</h3></p>" + pd.DataFrame(port_email).T.to_html(index=False)
            subject = '{} : Daily Summary - {}'.format(self.strategy_data.get('algo_name'), run_date)
            self.email_service.SendNotifications(subject, message)

            prev_run_update_sql = "update prev_run_date set date='{}' where algo_id={}".format(run_date, algo_id)
            with db_engine.connect() as connection:
                try:
                    for position in list(curr_positions):
                        if position in sold_list:
                            continue
                        insert_holding_sql = "Insert into daily_holdings (date, algo_id, holding_name, quantity, " \
                                             "buy_price, last_price) values ('{}',{},'{}',{},{},{})"\
                            .format(run_date, algo_id, position.sid.symbol, position.amount,
                                    round(position.cost_basis, 4), position.last_sale_price)
                        connection.execute(insert_holding_sql)
                    connection.execute(prev_run_update_sql)
                except Exception as e:
                    print(e)
            self.strategy_data.get('after_trading_end')(context, data)

    def before_trading_start(self, context, data):
        self.strategy_data.get('before_trading_start')(context, data)
        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.before_trading_start()

    def run_algorithm(self):
        live_trading = self.strategy_data.get('live_trading', False)
        # If live_trading true, trade with Virtual broker using database prices, else run normal backtest
        # database prices are updated from master_algo

        kwargs = {'start': self.strategy_data.get('start'),
                  'end': self.strategy_data.get('end'),
                  'initialize': self.initialize,
                  'handle_data': self.handle_data,
                  'analyze': self.analyze,
                  'before_trading_start': self.before_trading_start,
                  'bundle': 'quandl',
                  'capital_base': self.strategy_data.get('capital_base'),
                  'tws_uri': self.strategy_data.get('tws_uri'),
                  'live_trading': live_trading}

        run_algo_thread = threading.Thread(target=run_algorithm, kwargs=kwargs)
        run_algo_thread.start()

        if self.strategy_data.get('live_trading', False) is False:
            self.analyzer.show_plot()
            sys.exit(self.analyzer.app.exec_())

        run_algo_thread.join()
