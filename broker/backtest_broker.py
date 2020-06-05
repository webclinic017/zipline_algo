from datetime import datetime
from broker.broker import Broker


class BacktestBroker(Broker):
    def __init__(self):
        super().__init__()
        self.current_date = datetime.now().date()
        # self.commission = commission
        # self.algo_id = algo_id
        self.orders = dict()

    def get_portfolio(self, context):
        return context.portfolio

    def get_positions(self, context):
        return context.portfolio.positions

    def get_net(self, context):
        return context.portfolio.portfolio_value

    def get_cash(self, context):
        return context.portfolio.cash
