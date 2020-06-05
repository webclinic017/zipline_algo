title buy_hold_apple_backtest

set anaconda=c:\ProgramData\Anaconda3
set env=zipline

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

python algo.py --live_mode False

CALL %anaconda%\Scripts\deactivate.bat