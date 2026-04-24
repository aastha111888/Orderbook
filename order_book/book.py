from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional, Tuple

from sortedcontainers import SortedDict

from order_book.models import Order, OrderType, Side, Status, TimeInForce
from order_book.trade import Trade


def _bid_sort_key(price: float) -> float:
    return -price


def _ask_sort_key(price: float) -> float:
    return price


def _sync_status(order: Order) -> None:
    if order.remaining_qty <= 0:
        order.status = Status.FILLED
    elif order.filled_qty > 0:
        order.status = Status.PARTIAL


class OrderBook:
    """
    Price-time priority limit order book.

    Bids: highest price first; asks: lowest price first. FIFO per price level.
    """

    def __init__(self) -> None:
        self._bids: SortedDict[float, Deque[Order]] = SortedDict(_bid_sort_key)
        self._asks: SortedDict[float, Deque[Order]] = SortedDict(_ask_sort_key)
        self._orders: dict[str, Order] = {}

    def submit(self, order: Order) -> List[Trade]:
        """Match against the opposite side; rest remainder for GTC limit orders."""
        if order.side is Side.BUY:
            trades = self._match_buy(order)
        else:
            trades = self._match_sell(order)
        if order.remaining_qty > 0:
            if (
                order.order_type is OrderType.LIMIT
                and order.time_in_force is TimeInForce.GTC
                and order.price is not None
            ):
                self._rest(order)
            else:
                _sync_status(order)
        else:
            _sync_status(order)
        return trades

    def _limit_price(self, order: Order) -> Optional[float]:
        if order.order_type is OrderType.LIMIT:
            return order.price
        return None

    def _match_buy(self, order: Order) -> List[Trade]:
        trades: List[Trade] = []
        limit_px = self._limit_price(order)
        while order.remaining_qty > 0 and self._asks:
            best_price, _ = self._asks.peekitem(0)
            if limit_px is not None and best_price > limit_px:
                break
            trades.extend(self._consume_level(self._asks, best_price, order))
        return trades

    def _match_sell(self, order: Order) -> List[Trade]:
        trades: List[Trade] = []
        limit_px = self._limit_price(order)
        while order.remaining_qty > 0 and self._bids:
            best_price, _ = self._bids.peekitem(0)
            if limit_px is not None and best_price < limit_px:
                break
            trades.extend(self._consume_level(self._bids, best_price, order))
        return trades

    def _consume_level(
        self,
        side_book: SortedDict[float, Deque[Order]],
        level_price: float,
        aggressor: Order,
    ) -> List[Trade]:
        trades: List[Trade] = []
        queue = side_book[level_price]
        while queue and aggressor.remaining_qty > 0:
            resting = queue[0]
            qty = min(resting.remaining_qty, aggressor.remaining_qty)
            trades.append(
                Trade(
                    symbol=aggressor.symbol,
                    price=level_price,
                    quantity=qty,
                    aggressor_order_id=aggressor.order_id,
                    passive_order_id=resting.order_id,
                    aggressor_side=aggressor.side,
                )
            )
            resting.filled_qty += qty
            _sync_status(resting)
            aggressor.filled_qty += qty
            _sync_status(aggressor)
            if resting.remaining_qty <= 0:
                self._orders.pop(resting.order_id, None)
                queue.popleft()
        if not queue:
            del side_book[level_price]
        return trades

    def _rest(self, order: Order) -> None:
        if order.remaining_qty <= 0 or order.price is None:
            return
        book = self._bids if order.side is Side.BUY else self._asks
        if order.price not in book:
            book[order.price] = deque()
        book[order.price].append(order)
        self._orders[order.order_id] = order

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None:
            return False
        if order.price is not None:
            book = self._bids if order.side is Side.BUY else self._asks
            px = order.price
            if px in book:
                q = book[px]
                newq = deque(o for o in q if o.order_id != order_id)
                if len(newq) < len(q):
                    if newq:
                        book[px] = newq
                    else:
                        del book[px]
        order.status = Status.CANCELLED
        self._orders.pop(order_id, None)
        return True

    def spread(self) -> float | None:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb is None or ba is None:
            return None
        return ba[0] - bb[0]

    def snapshot(self, depth: int = 5) -> dict:
        bids: list[dict[str, float]] = []
        for i, (price, q) in enumerate(self._bids.items()):
            if i >= depth:
                break
            bids.append({"price": price, "qty": sum(o.remaining_qty for o in q)})
        asks: list[dict[str, float]] = []
        for i, (price, q) in enumerate(self._asks.items()):
            if i >= depth:
                break
            asks.append({"price": price, "qty": sum(o.remaining_qty for o in q)})
        return {"bids": bids, "asks": asks}

    def best_bid(self) -> Optional[Tuple[float, float]]:
        if not self._bids:
            return None
        price, q = self._bids.peekitem(0)
        return price, sum(o.remaining_qty for o in q)

    def best_ask(self) -> Optional[Tuple[float, float]]:
        if not self._asks:
            return None
        price, q = self._asks.peekitem(0)
        return price, sum(o.remaining_qty for o in q)
