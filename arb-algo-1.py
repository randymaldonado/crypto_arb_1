from binance.client import Client
import sys, time, math

API_KEY = ""
API_SECRET = ""
client = Client(API_KEY, API_SECRET, {"verify": True, "timeout": 20})

BTC = 'BTC'
ETH = 'ETH'
USD = 'USDT'


def find_best_symbol():
    return 'NULS'


def check_pnl(acc):
    x = float(acc[-1])-float(acc[0])
    return x


def price(symbol, comparison_symbol, type):
    depth = client.get_order_book(symbol=symbol+comparison_symbol)[type][0][0]
    return float(depth)


def arbitrage(symbol):
    """
    :param symbol: currency on which triangular arbitrage will be done.
    :type symbol: str
    :return:
    """
    capital = determine_capital()
    fee = .001
    BTC_USD = price(BTC, USD, "bids")
    SYM_USD = price(symbol, USD, 'bids')
    SYM_BTC = price(symbol, BTC, 'asks')
    SYM_ETH = price(symbol, ETH, 'asks')
    ETH_USD = price(ETH, USD, 'bids')

    # BUY SIDE
    nuls = float(int(capital / SYM_USD))
    btc = float(math.ceil(round(SYM_BTC * nuls, 6) * 100000) / 100000)
    eth = float(math.ceil(round(SYM_ETH * nuls, 6) * 100000) / 100000)

    # BTC return
    capital_btc = float(math.ceil(round(btc * BTC_USD, 6) * 100000) / 100000)
    capital_eth = float(math.ceil(round(eth * ETH_USD, 6) * 100000) / 100000)

    new_capital_btc = capital_btc * (1-fee) / BTC_USD * (1-fee) / SYM_BTC * (1-fee) * SYM_ETH * (1-fee) * ETH_USD
    new_capital_eth = capital_eth * (1-fee) / ETH_USD * (1-fee) / SYM_ETH * (1-fee) * SYM_BTC * (1-fee) * BTC_USD
    ret_btc = (new_capital_btc - capital_btc)/capital_btc * 100
    ret_eth = (new_capital_eth - capital_eth)/capital_eth * 100

    if ret_btc > .25:
        return 1

    elif ret_eth > .25:
        return -1

    else:
        return 0


def determine_capital():
    """
    Determines the capital to use per trade.
    :return: float type, amount of capital for trade.
    """
    x = float(client.get_asset_balance(USD)['free'])
    if x <= 1000.0:
        return x - 1.0
    else:
        return 1000.0


def buy(sym1, sym2):
    symbol = sym1+sym2
    x = determine_capital()
    nuls = float(int(x / price('NULS', USD, 'asks')))
    btc = float(math.ceil(round(price('NULS', BTC, 'asks') * nuls, 6)*100000)/100000)
    eth = float(math.ceil(round(price('NULS', ETH, 'asks') * nuls, 6)*100000)/100000)
    if symbol == 'BTCUSDT':
        quantity = btc
        prices = price(BTC, USD, 'asks')
        z = client.order_limit_buy(symbol=symbol, quantity=quantity, price=prices)['orderId']
        return z
    elif symbol == 'ETHUSDT':
        quantity = eth
        prices = price(ETH, USD, 'asks')
        z = client.order_limit_buy(symbol=symbol, quantity=quantity, price=prices)['orderId']
        return z
    elif symbol == 'NULSETH':
        quantity = float(int(float(client.get_asset_balance(sym2)['free']) / price(sym1, sym2, 'asks')))
        prices = price('NULS', ETH, 'asks')
        z = client.order_limit_buy(symbol=symbol, quantity=quantity, price=prices)['orderId']
        return z
    elif symbol == 'NULSBTC':
        quantity = float(int(float(client.get_asset_balance(sym2)['free']) / price(sym1, sym2, 'asks')))
        prices = price('NULS', BTC, 'asks')
        z = client.order_limit_buy(symbol=symbol, quantity=quantity, price=prices)['orderId']
        return z


def sell(sym1, sym2):
    symbol = sym1 + sym2
    prices = price(sym1, sym2, 'bids')
    if sym1 == 'NULS':
        quantity = float(client.get_asset_balance(sym1)['free'])

    else:
        a = float(client.get_asset_balance(sym1)['free'])
        quantity = float(math.floor(a*100000)/100000)

    x = client.order_limit_sell(symbol=symbol, quantity=quantity, price=prices)['orderId']
    return x


def check_trade(sym,order_id):
    # THIS FUNCTION IS STILL IFFY. NEED TO RUN SOME TESTS ON IT
    # TO MAKE SURE THAT THE WHILE LOOP WORKS WELL.

    x = client.get_order(symbol=sym, orderId=order_id)['status']

    if x == 'FILLED':
        return True
    else:
        time.sleep(4)
        x = client.get_order(symbol=sym, orderId=order_id)['status']
        if x == 'FILLED':
            return True
        else:
            time.sleep(6)
            x = client.get_order(symbol=sym, orderId=order_id)['status']
            if x == 'FILLED':
                return True
            else:
                return False


def liquidate(sym):
        btc_usd_order_id = client.get_open_orders(symbol=sym)[0]['orderId']
        quantity = client.get_open_orders(symbol=sym)[0]['executedQty']
        client.cancel_order(symbol=sym, orderId=btc_usd_order_id)
        client.order_market_sell(symbol=sym, quantity=quantity)
        time.sleep(5)


def trade(symbol):
    if arbitrage(symbol) == 1:
        order_id_1 = buy(BTC, USD)
        sym = BTC+USD
        if check_trade(sym, order_id_1) is True:
            order_id_2 = buy(symbol, BTC)
            sym = symbol+BTC
            if check_trade(sym, order_id_2) is True:
                order_id_3 = sell(symbol, ETH)
                sym = symbol+ETH
                if check_trade(sym, order_id_3) is True:
                    sell(ETH, USD)
                    time.sleep(3)
                    return client.get_asset_balance(USD)['free']
                else:
                    liquidate(sym)
                    return client.get_asset_balance(USD)['free']
            else:
                liquidate(sym)
                return client.get_asset_balance(USD)['free']
        else:
            liquidate(sym)
            return client.get_asset_balance(USD)['free']
    elif arbitrage(symbol) == -1:
        order_id_1 = buy(ETH, USD)
        sym = ETH+USD
        if check_trade(sym, order_id_1) is True:
            order_id_2 = buy(symbol, ETH)
            sym = symbol+ETH
            if check_trade(sym, order_id_2) is True:
                order_id_3 = sell(symbol, BTC)
                sym = symbol+BTC
                if check_trade(sym, order_id_3) is True:
                    sell(BTC, USD)
                    time.sleep(3)
                    return client.get_asset_balance(USD)['free']
                else:
                    liquidate(sym)
                    return client.get_asset_balance(USD)['free']
            else:
                liquidate(sym)
                return client.get_asset_balance(USD)['free']
        else:
            liquidate(sym)
            return client.get_asset_balance(USD)['free']
    else:
        return client.get_asset_balance(USD)['free']


def run():
    acc = [float(client.get_asset_balance(USD)['free'])]
    pnl = check_pnl(acc)
    symbol = find_best_symbol()
    while pnl <= 900.0:
        x = float(trade(symbol))
        acc.append(x)
        pnl = round(check_pnl(acc),2)
        x = 'Current PnL is: $' + str(pnl)
        y = 'Passes completed: ' + str(len(acc))
        z = x + '    ' + y
        sys.stdout.write('\r' + z)
    return print('Your profits today were $' + str(pnl) + '.')

run()
