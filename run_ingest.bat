title run ingest

set anaconda=C:\ProgramData\Anaconda3
set env=zipline

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

zipline ingest -b quandl

CALL %anaconda%\Scripts\deactivate.bat
