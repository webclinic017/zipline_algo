title run ingest

set anaconda=C:\ProgramData\Anaconda3
set env=zipline

CALL %anaconda%\Scripts\activate.bat %env%

set path=%anaconda%\Library\bin;%path%

zipline ingest -b quandl

CALL %anaconda%\Scripts\deactivate.bat

python alpha-compiler-master\alphacompiler\data\load_quandl_sf1.py

python alpha-compiler-master\alphacompiler\data\NASDAQ.py

python alpha-compiler-master\alphacompiler\data\NASDAQ_sector_code_loader.py
