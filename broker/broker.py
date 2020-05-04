from abc import ABC, abstractmethod


class Broker(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def pull_portfolio(self):
        pass

    @abstractmethod
    def order_target_percent(self):
        pass

    @abstractmethod
    def order_target(self):
        pass