from datetime import datetime
from utils.db_connector import DBConnector as dbc
from broker.broker import Broker


class VirtualBroker(Broker):
    def __init__(self, commission, algo_id):
        super().__init__()
        self.current_date = datetime.now().date()
        self.commission = commission
        self.algo_id = algo_id
        self.portfolio = dbc.fetch_portfolio(self.algo_id)
        self.orders = dict()

    def pull_portfolio(self):
        self.portfolio = dbc.update_portfolio(self.algo_id)