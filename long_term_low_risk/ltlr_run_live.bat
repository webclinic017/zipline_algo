title long_term_low_risk_live

set anaconda=c:\ProgramData\Anaconda3
set env=zipline-live

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

python ltlr_algo.py --live_mode ib

CALL %anaconda%\Scripts\deactivate.bat