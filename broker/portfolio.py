class Portfolio(object):
    def __init__(self, start_date=None, capital_base=0.0):
        self.cash_flow = 0.0
        self.portfolio_value = capital_base
        self.pnl = 0.0
        self.returns = 0.0
        self.cash = capital_base
        self.positions = Positions()
        self.start_date = start_date
        self.positions_value = 0.0
        self.positions_exposure = 0.0
