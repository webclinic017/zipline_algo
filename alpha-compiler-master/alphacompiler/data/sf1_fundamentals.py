
from alphacompiler.util.sparse_data import SparseDataFactor
from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
import os
from pathlib import Path
# TODO: this should be deleted and only included as an example
# this code should go with your application code.


class Fundamentals(SparseDataFactor):

    # outputs = ['accoci', 'assets', 'assetsavg', "yoy_sales", "qoq_earnings",
    #  'assetsc', 'assetsnc', 'assetturnover', 'bvps', 'capex', 'cashneq', 'cashnequsd', 'cor', 'consolinc',
    #  'currentratio', 'de', 'debt', 'debtc', 'debtnc', 'debtusd', 'deferredrev', 'depamor', 'deposits', 'divyield',
    #  'dps', 'ebit', 'ebitda', 'ebitdamargin', 'ebitdausd', 'ebitusd', 'ebt', 'eps', 'epsdil', 'epsusd', 'equity',
    #  'equityavg', 'equityusd', 'ev', 'evebit', 'evebitda', 'fcf', 'fcfps', 'fxusd', 'gp', 'grossmargin', 'intangibles',
    #  'intexp', 'invcap', 'invcapavg', 'inventory', 'investments', 'investmentsc', 'investmentsnc', 'liabilities',
    #  'liabilitiesc', 'liabilitiesnc', 'marketcap', 'ncf', 'ncfbus', 'ncfcommon', 'ncfdebt', 'ncfdiv', 'ncff', 'ncfi',
    #  'ncfinv', 'ncfo', 'ncfx', 'netinc', 'netinccmn', 'netinccmnusd', 'netincdis', 'netincnci', 'netmargin', 'opex',
    #  'opinc', 'payables', 'payoutratio', 'pb', 'pe', 'pe1', 'ppnenet', 'prefdivis', 'price', 'ps', 'ps1', 'receivables',
    #  'retearn', 'revenue', 'revenueusd', 'rnd', 'roa', 'roe', 'roic', 'ros', 'sbcomp', 'sgna', 'sharefactor',
    #  'sharesbas', 'shareswa', 'shareswadil', 'sps', 'tangibles', 'taxassets', 'taxexp', 'taxliabilities', 'tbvps',
    #  'workingcapital']

    outputs = ['assets', 'capex', 'cor', 'currentratio', 'de', 'debt', 'divyield', 'ebit', 'ebitda', 'ebt', 'eps', 'fcf',
              'grossmargin', 'inventory', 'investments', 'liabilities', 'marketcap', 'ncf', 'netinc', 'netmargin',
              'opex', 'payables', 'payoutratio', 'pb', 'pe', 'receivables', 'revenue', 'rnd', 'roa', 'roe', 'sgna',
              'taxassets', 'taxliabilities', 'workingcapital', 'yoy_sales', 'qoq_earnings']

    def __init__(self, *args, **kwargs):
        super(Fundamentals, self).__init__(*args, **kwargs)
        self.N = len(get_ticker_sid_dict_from_bundle("quandl")) + 1  # max(sid)+1 get this from the bundle
        self.data_path = os.path.join(str(Path.home()), "SF1.npy")
