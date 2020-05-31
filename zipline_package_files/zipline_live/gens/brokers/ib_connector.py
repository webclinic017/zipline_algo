from collections import defaultdict, OrderedDict
from time import sleep
import numpy as np

from ib.ext.EClientSocket import EClientSocket
from ib.ext.EWrapper import EWrapper
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.ExecutionFilter import ExecutionFilter
from ib.ext.EClientErrors import EClientErrors

symbol_to_exchange = defaultdict(lambda: 'SMART')
symbol_to_exchange['VIX'] = 'CBOE'
symbol_to_exchange['GLD'] = 'ARCA'
symbol_to_exchange['GDX'] = 'ARCA'

symbol_to_sec_type = defaultdict(lambda: 'STK')
symbol_to_sec_type['VIX'] = 'IND'

_connection_timeout = 15  # Seconds
_poll_frequency = 0.1


def log_message(message, mapping):
    try:
        del (mapping['self'])
    except (KeyError,):
        pass
    items = list(mapping.items())
    items.sort()
    log.debug(('### %s' % (message,)))
    for k, v in items:
        log.debug(('    %s:%s' % (k, v)))


class TWSConnection(EClientSocket, EWrapper):
    def __init__(self, tws_uri):
        EWrapper.__init__(self)
        EClientSocket.__init__(self, anyWrapper=self)

        self.tws_uri = tws_uri
        host, port, client_id = self.tws_uri.split(':')
        self._host = host
        self._port = int(port)
        self.client_id = int(client_id)

        self._next_ticker_id = 0
        self._next_request_id = 0
        self._next_order_id = None
        self.managed_accounts = None
        self.symbol_to_ticker_id = {}
        self.ticker_id_to_symbol = {}
        self.last_tick = defaultdict(dict)
        self.bars = {}
        # accounts structure: accounts[account_id][currency][value]
        self.accounts = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: np.NaN)))
        self.accounts_download_complete = False
        self.positions = {}
        self.portfolio = {}
        self.open_orders = {}
        self.order_statuses = {}
        self.executions = defaultdict(OrderedDict)
        self.commissions = defaultdict(OrderedDict)
        self._execution_to_order_id = {}
        self.time_skew = None
        self.unrecoverable_error = False

        self.connect()
        # self.reqMarketDataType(3)

    def connect(self):
        log.info("Connecting: {}:{}:{}".format(self._host, self._port,
                                               self.client_id))
        self.eConnect(self._host, self._port, self.client_id)
        timeout = _connection_timeout
        while timeout and not self.isConnected():
            sleep(_poll_frequency)
            timeout -= _poll_frequency
        else:
            if not self.isConnected():
                raise SystemError("Connection timeout during TWS connection!")

        self._download_account_details()
        log.info("Managed accounts: {}".format(self.managed_accounts))

        self.reqCurrentTime()
        self.reqIds(1)

        while self.time_skew is None or self._next_order_id is None:
            sleep(_poll_frequency)

        log.info("Local-Broker Time Skew: {}".format(self.time_skew))

    def _download_account_details(self):
        exec_filter = ExecutionFilter()
        exec_filter.m_clientId = self.client_id
        self.reqExecutions(self.next_request_id, exec_filter)

        self.reqManagedAccts()
        while self.managed_accounts is None:
            sleep(_poll_frequency)

        for account in self.managed_accounts:
            self.reqAccountUpdates(subscribe=True, acctCode=account)
        while self.accounts_download_complete is False:
            sleep(_poll_frequency)

    @property
    def next_ticker_id(self):
        ticker_id = self._next_ticker_id
        self._next_ticker_id += 1
        return ticker_id

    @property
    def next_request_id(self):
        request_id = self._next_request_id
        self._next_request_id += 1
        return request_id

    @property
    def next_order_id(self):
        order_id = self._next_order_id
        self._next_order_id += 1
        return order_id

    def subscribe_to_market_data(self,
                                 symbol,
                                 sec_type='STK',
                                 exchange='SMART',
                                 currency='USD'):
        if symbol in self.symbol_to_ticker_id:
            # Already subscribed to market data
            return

        contract = Contract()
        contract.m_symbol = symbol
        contract.m_secType = symbol_to_sec_type[symbol]
        contract.m_exchange = symbol_to_exchange[symbol]
        contract.m_currency = currency
        self.reqMarketDataType(4)
        ticker_id = self.next_ticker_id

        self.symbol_to_ticker_id[symbol] = ticker_id
        self.ticker_id_to_symbol[ticker_id] = symbol

        tick_list = "233"  # RTVolume, return tick_type == 48
        self.reqMktData(ticker_id, contract, tick_list, False)

    def _process_tick(self, ticker_id, tick_type, value):
        try:
            symbol = self.ticker_id_to_symbol[ticker_id]
        except KeyError:
            log.error("Tick {} for id={} is not registered".format(tick_type,
                                                                   ticker_id))
            return
        if tick_type == 68:
            # RT Volume Bar. Format:
            # Last trade price; Last trade size;Last trade time;Total volume;\
            # VWAP;Single trade flag
            # e.g.: 701.28;1;1348075471534;67854;701.46918464;true
            # (last_trade_price, last_trade_size, last_trade_time, total_volume,
            #  vwap, single_trade_flag) = value.split(';')
            last_trade_price = str(value)
            last_trade_size = 0
            last_trade_time = 0
            total_volume = 0
            vwap = 0
            single_trade_flag = 'true'

            # Ignore this update if last_trade_price is empty:
            # tickString: tickerId=0 tickType=48/RTVolume ;0;1469805548873;\
            # 240304;216.648653;true
            if len(last_trade_price) == 0:
                return

            # last_trade_dt = pd.to_datetime(float(last_trade_time), unit='ms',
            #                                utc=True)
            last_trade_dt = pd.to_datetime('now', utc=True)
            self._add_bar(symbol, float(last_trade_price),
                          int(last_trade_size), last_trade_dt,
                          int(total_volume), float(vwap),
                          single_trade_flag)

    def _add_bar(self, symbol, last_trade_price, last_trade_size,
                 last_trade_time, total_volume, vwap, single_trade_flag):
        bar = pd.DataFrame(index=pd.DatetimeIndex([last_trade_time]),
                           data={'last_trade_price': last_trade_price,
                                 'last_trade_size': last_trade_size,
                                 'total_volume': total_volume,
                                 'vwap': vwap,
                                 'single_trade_flag': single_trade_flag})

        if symbol not in self.bars:
            self.bars[symbol] = bar
        else:
            self.bars[symbol] = self.bars[symbol].append(bar)

    def tickPrice(self, ticker_id, field, price, can_auto_execute):
        self._process_tick(ticker_id, tick_type=field, value=price)

    def tickSize(self, ticker_id, field, size):
        self._process_tick(ticker_id, tick_type=field, value=size)

    def tickOptionComputation(self,
                              ticker_id, field, implied_vol, delta, opt_price,
                              pv_dividend, gamma, vega, theta, und_price):
        log_message('tickOptionComputation', vars())

    def tickGeneric(self, ticker_id, tick_type, value):
        self._process_tick(ticker_id, tick_type=tick_type, value=value)

    def tickString(self, ticker_id, tick_type, value):
        self._process_tick(ticker_id, tick_type=tick_type, value=value)

    def tickEFP(self, ticker_id, tick_type, basis_points,
                formatted_basis_points, implied_future, hold_days,
                future_expiry, dividend_impact, dividends_to_expiry):
        log_message('tickEFP', vars())

    def updateAccountValue(self, key, value, currency, account_name):
        self.accounts[account_name][currency][key] = value

    def updatePortfolio(self,
                        contract,
                        position,
                        market_price,
                        market_value,
                        average_cost,
                        unrealized_pnl,
                        realized_pnl,
                        account_name):
        symbol = contract.m_symbol

        position = Position(contract=contract,
                            position=position,
                            market_price=market_price,
                            market_value=market_value,
                            average_cost=average_cost,
                            unrealized_pnl=unrealized_pnl,
                            realized_pnl=realized_pnl,
                            account_name=account_name)

        self.positions[symbol] = position

    def updateAccountTime(self, time_stamp):
        pass

    def accountDownloadEnd(self, account_name):
        self.accounts_download_complete = True

    def nextValidId(self, order_id):
        self._next_order_id = order_id

    def contractDetails(self, req_id, contract_details):
        log_message('contractDetails', vars())

    def contractDetailsEnd(self, req_id):
        log_message('contractDetailsEnd', vars())

    def bondContractDetails(self, req_id, contract_details):
        log_message('bondContractDetails', vars())

    def orderStatus(self, order_id, status, filled, remaining, avg_fill_price,
                    perm_id, parent_id, last_fill_price, client_id, why_held):
        self.order_statuses[order_id] = _method_params_to_dict(vars())

        log.debug(
            "Order-{order_id} {status}: "
            "filled={filled} remaining={remaining} "
            "avg_fill_price={avg_fill_price} "
            "last_fill_price={last_fill_price} ".format(
                order_id=order_id,
                status=self.order_statuses[order_id]['status'],
                filled=self.order_statuses[order_id]['filled'],
                remaining=self.order_statuses[order_id]['remaining'],
                avg_fill_price=self
                .order_statuses[order_id]['avg_fill_price'],
                last_fill_price=self
                .order_statuses[order_id]['last_fill_price']))

    def openOrder(self, order_id, contract, order, state):
        self.open_orders[order_id] = _method_params_to_dict(vars())

        log.debug(
            "Order-{order_id} {status}: "
            "{order_action} {order_count} {symbol} with {order_type} order. "
            "limit_price={limit_price} stop_price={stop_price}".format(
                order_id=order_id,
                status=state.m_status,
                order_action=order.m_action,
                order_count=order.m_totalQuantity,
                symbol=contract.m_symbol,
                order_type=order.m_orderType,
                limit_price=order.m_lmtPrice,
                stop_price=order.m_auxPrice))

    def openOrderEnd(self):
        pass

    def execDetails(self, req_id, contract, exec_detail):
        order_id, exec_id = exec_detail.m_orderId, exec_detail.m_execId
        self.executions[order_id][exec_id] = _method_params_to_dict(vars())
        self._execution_to_order_id[exec_id] = order_id

        log.info(
            "Order-{order_id} executed @ {exec_time}: "
            "{symbol} current: {shares} @ ${price} "
            "total: {cum_qty} @ ${avg_price} "
            "exec_id: {exec_id} by client-{client_id}".format(
                order_id=order_id, exec_id=exec_id,
                exec_time=pd.to_datetime(exec_detail.m_time),
                symbol=contract.m_symbol,
                shares=exec_detail.m_shares,
                price=exec_detail.m_price,
                cum_qty=exec_detail.m_cumQty,
                avg_price=exec_detail.m_avgPrice,
                client_id=exec_detail.m_clientId))

    def execDetailsEnd(self, req_id):
        log.debug(
            "Execution details completed for request {req_id}".format(
                req_id=req_id))

    def commissionReport(self, commission_report):
        exec_id = commission_report.m_execId
        order_id = self._execution_to_order_id[commission_report.m_execId]
        self.commissions[order_id][exec_id] = commission_report

        log.debug(
            "Order-{order_id} report: "
            "realized_pnl: ${realized_pnl} "
            "commission: ${commission} yield: {yield_} "
            "exec_id: {exec_id}".format(
                order_id=order_id,
                exec_id=commission_report.m_execId,
                realized_pnl=commission_report.m_realizedPNL
                if commission_report.m_realizedPNL != sys.float_info.max
                else 0,
                commission=commission_report.m_commission,
                yield_=commission_report.m_yield
                if commission_report.m_yield != sys.float_info.max
                else 0)
        )

    def connectionClosed(self):
        self.unrecoverable_error = True
        log.error("IB Connection closed")

    def error(self, id_=None, error_code=None, error_msg=None):
        if isinstance(id_, Exception):
            # XXX: for an unknown reason 'log' is None in this branch,
            # therefore it needs to be instantiated before use
            global log
            if not log:
                log = Logger('Virtual Broker')
            log.exception(id_)

        if isinstance(error_code, EClientErrors.CodeMsgPair):
            error_msg = error_code.msg()
            error_code = error_code.code()

        if isinstance(error_code, int):
            if error_code in (502, 503, 326):
                # 502: Couldn't connect to TWS.
                # 503: The TWS is out of date and must be upgraded.
                # 326: Unable connect as the client id is already in use.
                self.unrecoverable_error = True

            if error_code < 1000:
                log.error("[{}] {} ({})".format(error_code, error_msg, id_))
            else:
                log.info("[{}] {} ({})".format(error_code, error_msg, id_))
        else:
            log.error("[{}] {} ({})".format(error_code, error_msg, id_))

    def updateMktDepth(self, ticker_id, position, operation, side, price,
                       size):
        log_message('updateMktDepth', vars())

    def updateMktDepthL2(self, ticker_id, position, market_maker, operation,
                         side, price, size):
        log_message('updateMktDepthL2', vars())

    def updateNewsBulletin(self, msg_id, msg_type, message, orig_exchange):
        log_message('updateNewsBulletin', vars())

    def managedAccounts(self, accounts_list):
        self.managed_accounts = accounts_list.split(',')

    def receiveFA(self, fa_data_type, xml):
        log_message('receiveFA', vars())

    def historicalData(self, req_id, date, open_, high, low, close, volume,
                       count, wap, has_gaps):
        log_message('historicalData', vars())

    def scannerParameters(self, xml):
        log_message('scannerParameters', vars())

    def scannerData(self, req_id, rank, contract_details, distance, benchmark,
                    projection, legs_str):
        log_message('scannerData', vars())

    def currentTime(self, time):
        self.time_skew = (pd.to_datetime('now', utc=True) -
                          pd.to_datetime(long(time), unit='s', utc=True))

    def deltaNeutralValidation(self, req_id, under_comp):
        log_message('deltaNeutralValidation', vars())

    def fundamentalData(self, req_id, data):
        log_message('fundamentalData', vars())

    def marketDataType(self, req_id, market_data_type):
        log_message('marketDataType', vars())

    def realtimeBar(self, req_id, time, open_, high, low, close, volume, wap,
                    count):
        log_message('realtimeBar', vars())

    def scannerDataEnd(self, req_id):
        log_message('scannerDataEnd', vars())

    def tickSnapshotEnd(self, req_id):
        log_message('tickSnapshotEnd', vars())

    def position(self, account, contract, pos, avg_cost):
        log_message('position', vars())

    def positionEnd(self):
        log_message('positionEnd', vars())

    def accountSummary(self, req_id, account, tag, value, currency):
        log_message('accountSummary', vars())

    def accountSummaryEnd(self, req_id):
        log_message('accountSummaryEnd', vars())


