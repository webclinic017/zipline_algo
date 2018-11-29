# zipline_algo

1. installed conda
2. create env called zipline (conda create -n zipline python=3.5)
3. installed zipline using conda install (conda install -c quantopian zipline)
4. Set QUANDL_API_KEY in environment variable
5. ingest data using "zipline ingest -b quandl"
6. pip install quandl
7. download quandl loader from http://alphacompiler.com/blog/6/
8. copy NASDAQ_sids.npy and SF!.npy to ..envs\zipline\Lib\site-packages\alphacompiler\data or load data using alphacompiler (link in step 7)
