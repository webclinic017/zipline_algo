from iexfinance.stocks import Stock
from pathlib import Path
import os
import pandas as pd

def get_benchmark_returns(symbol):

    data = Stock(symbol, output_format='pandas', token="sk_50c3da6c160b4326999c04fb57c1fb25")
    history = pd.read_csv(os.path.join(str(Path.home()), 'SPY_benchmark.csv'), index_col='date', parse_dates=True)
    df = data.get_historical_prices(range='5y')
    df = df['close'].pct_change()
    df = pd.concat([history['close'], df])
    df = df.loc[~df.index.duplicated(keep='first')]
    # return df.sort_index().tz_localize('UTC').pct_change(1).iloc[1:]
    return df.sort_index().tz_localize('UTC')

