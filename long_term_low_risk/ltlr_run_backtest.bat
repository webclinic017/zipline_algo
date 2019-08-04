title long_term_low_risk_backtest

set anaconda=c:\ProgramData\Anaconda3
set env=zipline

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

python ltlr_algo.py --live_mode False

CALL %anaconda%\Scripts\deactivate.bat