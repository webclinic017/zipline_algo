from abc import ABC, ABCMeta, abstractmethod
from PyQt5 import QtWidgets
from sip import wrappertype as pyqtWrapperType
# from PyQt5.QtCore import pyqtWrapperType


class FinalMeta(pyqtWrapperType, metaclass=ABCMeta):
    pass


class AnalysisTab(QtWidgets.QWidget):
    @abstractmethod
    def get_tab_name(self):
        pass

    @abstractmethod
    def get_tab_menu(self):
        pass

    @abstractmethod
    def get_tab_description(self):
        pass

    @abstractmethod
    def update_plot(self, analysis_data):
        pass

    def generate_report(self):
        pass
