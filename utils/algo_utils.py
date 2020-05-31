def get_run_mode(mode):
    tws_uri = None
    live_trading = False
    if mode == 'ib':
        print("Running in live mode with Interactive broker")
        tws_uri = 'localhost:7497:1232'
        live_trading = True
    elif mode == 'virtual':
        print("Running in live mode with Virtual broker")
        live_trading = True
    elif mode == 'backtest':
        print("Running in backtest mode")

    return tws_uri, live_trading
