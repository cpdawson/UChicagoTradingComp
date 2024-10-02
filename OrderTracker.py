from collections import OrderedDict, namedtuple
from xchangelib import xchange_client

Order = namedtuple("Order", "qty side price")
Trade = namedtuple("Trade", "timestamp price qty")


class OrderTracker:
    def __init__(self):
        self.bids: dict[int, Order] = {}  # order_id -> (price, qty)
        self.asks: dict[int, Order] = {}  # order_id -> (price, qty)

    def add_order(self, id: int, qty: int, side: xchange_client.Side, price: str):
        if side == "BUY":
            self.bids[id] = Order(qty, side, price)
        elif side == "SELL":
            self.asks[id] = Order(qty, side, price)

    def cancel_order(self, id: int):
        if id in self.bids:
            self.bids.pop(id)
        elif id in self.asks:
            self.asks.pop(id)

    def fill_order(self, id: int, qty: int, price: str):
        if id in self.bids:
            self.bids[id] = Order(self.bids[id].price, self.bids[id].qty - qty, self.bids[id].side)
            if self.bids[id].qty == 0:
                self.bids.pop(id)
        elif id in self.asks:
            self.asks[id] = Order(self.asks[id].price, self.asks[id].qty - qty, self.asks[id].side)
            if self.asks[id].qty == 0:
                self.asks.pop(id)

    def get_order(self, id: int) -> Order:
        if id in self.bids:
            return self.bids[id]
        elif id in self.asks:
            return self.asks[id]

    def __str__(self) -> str:
        return f"bids: {self.bids}, asks: {self.asks}"