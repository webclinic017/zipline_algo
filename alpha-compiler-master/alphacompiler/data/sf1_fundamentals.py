
from alphacompiler.util.sparse_data import SparseDataFactor
from alphacompiler.util.zipline_data_tools import get_ticker_sid_dict_from_bundle
import os
from pathlib import Path
# TODO: this should be deleted and only included as an example
# this code should go with your application code.


class Fundamentals(SparseDataFactor):
    # outputs = ["ROE_ART", "BVPS_ARQ", "SPS_ART", "FCFPS_ARQ", "PRICE"]
    outputs = ["revenue", "rnd", "netinc", "eps", "liabilities", "ebt", "ebitda", "dps", "marketcap", "gp", "pe", "ps1",
               "divyield", "price", "yoy_sales", "qoq_earnings"]

    def __init__(self, *args, **kwargs):
        super(Fundamentals, self).__init__(*args, **kwargs)
        self.N = len(get_ticker_sid_dict_from_bundle("quandl")) + 1  # max(sid)+1 get this from the bundle
        self.data_path = os.path.join(str(Path.home()), "SF1.npy")
