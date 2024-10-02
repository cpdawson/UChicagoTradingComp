from typing import Optional

from xchangelib import xchange_client
import asyncio
from OrderTracker import OrderTracker, Trade
from collections import defaultdict, OrderedDict
from datetime import datetime


class MyXchangeClient(xchange_client.XChangeClient):
    '''A shell client with the methods that can be implemented to interact with the xchange.'''
    def __init__(self, host: str, username: str, password: str):
        super().__init__(host, username, password)
        self.symbols = {"JMS", "EPT", "DLO", "MKU", "IGM", "BRV", "SCP", "JAK"}
        self.order_trackers: dict[str, OrderTracker] = {symbol: OrderTracker() for symbol in self.symbols}
        self.id_to_symbol: defaultdict[int, str] = defaultdict(str)
        self.start_time = datetime.now()
        self.counter = 0
        self.rejected_count = 0
        self.failed_cancel_count = 0
        self.max_order_size = 100
        self.max_absolute_position_size = 1000
        self.max_directional_position_size = 10

    async def bot_handle_cancel_response(self, order_id: str, success: bool, error: Optional[str]) -> None:
        if success:
            symbol = self.id_to_symbol[order_id]
            self.order_trackers[symbol].cancel_order(order_id)
        else:
            self.failed_cancel_count += 1

    async def bot_handle_order_fill(self, order_id: str, qty: int, price: int):
        self.order_trackers[self.id_to_symbol[order_id]].fill_order(order_id, qty, price)

    async def bot_handle_order_rejected(self, order_id: str, reason: str) -> None:
        self.rejected_count += 1
        last_order = self.order_trackers[self.id_to_symbol[order_id]].get_order(order_id)
        self.order_trackers[self.id_to_symbol[order_id]].cancel_order(order_id)
        if last_order is None:
            return
        await self.place_and_track_order(self.id_to_symbol[order_id], last_order.qty, last_order.side, last_order.price)

    async def bot_handle_trade_msg(self, symbol: str, price: int, qty: int):
        pass

    async def compute_largest_order(self):
        symbols = ['BRV', 'DLO', 'EPT', 'IGM', 'JAK', 'JMS', 'MKU', 'SCP']
        order_size = 40
        with open('outputs.txt', 'a') as file:  # Open the file in append mode
            for symbol in symbols:
                book = self.order_books[symbol]
                sorted_bids = sorted((v, k) for v, k in book.bids.items() if v != 0)
                sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
                if sorted_bids:
                    large_order = sorted_bids[0]
                    if large_order[1] > 120 and self.positions[symbol] <= 160:
                        if self.order_trackers[symbol].__init__() is not None:
                            orders = self.order_trackers[symbol].__init__().bids
                            if (large_order[0] - 1) not in orders:
                                pass
                        else:
                            file.write("BUY\n")
                            print("BUY")# Write to the file instead of printing

                if sorted_asks:
                    large_order = sorted_asks[0]
                    if large_order[1] > 120 and self.positions[symbol] >= -160:
                        if self.order_trackers[symbol].__init__() is not None:
                            orders = self.order_trackers[symbol].__init__().asks
                            if (large_order[0] - 1) not in orders:
                                file.write("SELL\n")  # Write to the file instead of printing
                                print("SELL")
                            else:
                                pass
                        else:
                            file.write("SELL\n")  # Write to the file instead of printing
                            print("SELL")

    async def bot_handle_book_update(self, symbol: str) -> None:
        pass
    async def bot_handle_swap_response(self, swap: str, qty: int, success: bool):
        ...

    async def trade(self):
        """This is a task that is started right before the bot connects and runs in the background."""
        while True:
            await asyncio.sleep(.15)
            await self.compute_largest_order()
            # await self.check_arb_SCP()
            # await self.check_arb_JAK()
            # await self.offload()

    async def place_orders(self):
        for symbol, book in self.order_trackers.items():
            await self.place_orders_symbol(symbol)
        pnl = await self.compute_pnl()
        # print(
        #     f"Current PnL: {pnl}; Current rejected count: {self.rejected_count}; Current failed cancel count: {self.failed_cancel_count};")

    async def offload(self):
        for symbol, position in self.positions.items():
            if symbol == 'cash':
                continue
            if position > self.max_directional_position_size:
                await self.place_and_track_order(symbol, position, xchange_client.Side.SELL)
            elif position < -self.max_directional_position_size:
                await self.place_and_track_order(symbol, -position, xchange_client.Side.BUY)

    async def view_books(self):
        """Prints the books every 3 seconds."""
        while True:
            await asyncio.sleep(.5)
            for security, book in self.order_books.items():
                sorted_bids = sorted((k, v) for k, v in book.bids.items() if v != 0)
                sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
            #     print(f"Bids for {security}:\n{sorted_bids}")
            #     print(f"Asks for {security}:\n{sorted_asks}")
            #     print(f"Orders {self.order_trackers[security]}")
            # pnl = await self.compute_pnl()
            # print(
            #     f"Current PnL: {pnl}; Current rejected count: {self.rejected_count}; Current failed cancel count: {self.failed_cancel_count}")

    async def compute_pnl(self):
        pnl = 0
        for symbol in self.positions:
            pnl += self.positions[symbol] * (await self.compute_fair_price(symbol))
        return pnl

    async def compute_best_bid_ask(self, symbol: str) -> tuple[int, int]:
        """Returns the best bid and ask prices of a security."""
        book = self.order_books[symbol]
        sorted_bids = sorted((k, v) for k, v in book.bids.items() if v != 0)
        sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
        if not sorted_bids or not sorted_asks:
            return 0, 0
        best_bid = sorted_bids[-1][0]
        best_ask = sorted_asks[-1][0]
        return best_bid, best_ask

    async def compute_fair_price(self, symbol: str) -> int:
        """Returns the fair price of a security."""
        if symbol == 'cash':
            return 1
        book = self.order_books[symbol]
        sorted_bids = sorted((k, v) for k, v in book.bids.items() if v != 0)
        sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
        if not sorted_bids or not sorted_asks:
            return await self.get_last_traded_price(symbol)
        best_bid = sorted_bids[-1][0]
        best_ask = sorted_asks[-1][0]
        return (best_bid + best_ask) // 2

    async def get_last_traded_price(self, symbol: str) -> int:
        """Returns the last traded price of a security."""
        if not self.trade_histories[symbol]:
            return 0
        return self.trade_histories[symbol][-1].price

    async def start(self):
        """
        Creates tasks that can be run in the background. Then connects to the exchange
        and listens for messages.
        """
        asyncio.create_task(self.trade())
        asyncio.create_task(self.view_books())
        await self.connect()

    async def check_arb_SCP(self):
        SCP_bid, SCP_ask = await self.compute_best_bid_ask("SCP")
        EPT_bid, EPT_ask = await self.compute_best_bid_ask("EPT")
        IGM_bid, IGM_ask = await self.compute_best_bid_ask("IGM")
        BRV_bid, BRV_ask = await self.compute_best_bid_ask("BRV")
        size_multiplier = 3
        if SCP_bid == 0 or SCP_ask == 0 or EPT_bid == 0 or EPT_ask == 0 or IGM_bid == 0 or IGM_ask == 0 or BRV_bid == 0 or BRV_ask == 0:
            return
        if SCP_ask * 10 + 7 < EPT_bid * 3 + IGM_bid * 3 + BRV_bid * 4:
            await self.place_and_track_order("SCP", 10 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("EPT", 3 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("IGM", 3 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("BRV", 4 * size_multiplier, xchange_client.Side.SELL)
            await self.place_swap_order("fromSCP", size_multiplier)
        elif SCP_bid * 10 > EPT_ask * 3 + IGM_ask * 3 + BRV_ask * 4 + 7:
            await self.place_and_track_order("SCP", 10 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("EPT", 3 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("IGM", 3 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("BRV", 4 * size_multiplier, xchange_client.Side.BUY)
            await self.place_swap_order("toSCP", size_multiplier)
            ...

    async def check_arb_JAK(self):
        # JAK = 2 EPT + 5 DLO + 3 MKU
        JAK_bid, JAK_ask = await self.compute_best_bid_ask("JAK")
        EPT_bid, EPT_ask = await self.compute_best_bid_ask("EPT")
        DLO_bid, DLO_ask = await self.compute_best_bid_ask("DLO")
        MKU_bid, MKU_ask = await self.compute_best_bid_ask("MKU")
        size_multiplier = 3
        if JAK_bid == 0 or JAK_ask == 0 or EPT_bid == 0 or EPT_ask == 0 or DLO_bid == 0 or DLO_ask == 0 or MKU_bid == 0 or MKU_ask == 0:
            return
        if JAK_ask * 10 + 7 < EPT_bid * 2 + DLO_bid * 5 + MKU_bid * 3:
            await self.place_and_track_order("JAK", 10 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("EPT", 2 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("DLO", 5 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("MKU", 3 * size_multiplier, xchange_client.Side.SELL)
            await self.place_swap_order("fromJAK", size_multiplier)
        elif JAK_bid * 10 > EPT_ask * 2 + DLO_ask * 5 + MKU_ask * 3 + 7:
            await self.place_and_track_order("JAK", 10 * size_multiplier, xchange_client.Side.SELL)
            await self.place_and_track_order("EPT", 2 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("DLO", 5 * size_multiplier, xchange_client.Side.BUY)
            await self.place_and_track_order("MKU", 3 * size_multiplier, xchange_client.Side.BUY)
            await self.place_swap_order("toJAK", size_multiplier)

    async def place_and_track_order(self, symbol: str, qty: int, side: xchange_client.Side, price: int = -1) -> int:
        if price == -1:
            order_id = await self.place_order(symbol, qty, side)
        else:
            order_id = await self.place_order(symbol, qty, side, price)
        self.order_trackers[symbol].add_order(order_id, price, qty, side)
        self.id_to_symbol[order_id] = symbol
        return order_id


async def main():
    SERVER = 'staging.uchicagotradingcompetition.com:3333'  # run on sandbox
    my_client = MyXchangeClient(SERVER, "upenn1", "rattata-zapdos-3060")
    await my_client.start()
    return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())