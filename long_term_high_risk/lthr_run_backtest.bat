title long_term_high_risk_live

set anaconda=c:\ProgramData\Anaconda3
set env=zipline

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

python lthr_algo.py --live_mode False

CALL %anaconda%\Scripts\deactivate.bat