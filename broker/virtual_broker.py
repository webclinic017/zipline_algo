from datetime import datetime
from utils.db_connector import DBConnector
from broker.broker import Broker


class VirtualBroker(Broker):
    def __init__(self, commission, algo_id):
        super().__init__()
        self.dbc = DBConnector()
        self.current_date = datetime.now().date()
        self.commission = commission
        self.algo_id = algo_id
        self.portfolio = self.dbc.fetch_portfolio(algo_id)
        self.orders = dict()

    def get_portfolio(self, context):
        self.portfolio = self.dbc.update_portfolio(self.algo_id)