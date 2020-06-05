title mid_term_low_risk_live

set anaconda=c:\ProgramData\Anaconda3
set env=zipline-live

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

python mtlr_algo.py --live_mode True

CALL %anaconda%\Scripts\deactivate.bat