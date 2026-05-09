from NorenRestApiPy.NorenApi import NorenApi
import concurrent.futures
import time

class Order:
    def __init__(self, buy_or_sell=None, product_type=None, exchange=None,
                 tradingsymbol=None, price_type=None, quantity=None,
                 price=None, trigger_price=None, discloseqty=0,
                 retention='DAY', remarks='tag', order_id=None):
        self.buy_or_sell    = buy_or_sell
        self.product_type   = product_type
        self.exchange       = exchange
        self.tradingsymbol  = tradingsymbol
        self.quantity       = quantity
        self.discloseqty    = discloseqty
        self.price_type     = price_type
        self.price          = price
        self.trigger_price  = trigger_price
        self.retention      = retention
        self.remarks        = remarks
        self.order_id       = order_id


class NorenApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self,
            host='https://piconnect.flattrade.in/PiConnectAPI/',
            websocket='wss://piconnect.flattrade.in/PiConnectWSAPI/')

    def place_basket(self, orders):
        resp_err, resp_ok, result = 0, 0, []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_order = {executor.submit(self.place_order, order): order for order in orders}
            for future in concurrent.futures.as_completed(future_to_order):
                try:
                    result.append(future.result())
                    resp_ok += 1
                except Exception as exc:
                    print(exc)
                    resp_err += 1
        return result

    def placeOrder(self, order: Order):
        return NorenApi.place_order(self,
            buy_or_sell=order.buy_or_sell, product_type=order.product_type,
            exchange=order.exchange, tradingsymbol=order.tradingsymbol,
            quantity=order.quantity, discloseqty=order.discloseqty,
            price_type=order.price_type, price=order.price,
            trigger_price=order.trigger_price, retention=order.retention,
            remarks=order.remarks)
