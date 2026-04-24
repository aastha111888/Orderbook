import pytest

from order_book.book import OrderBook
from order_book.models import (
    Order,
    OrderType,
    Side,
    Status,
    TimeInForce,
    make_order_id,
)


@pytest.fixture
def book() -> OrderBook:
    return OrderBook()


@pytest.fixture
def limit_order():
    def _limit(
        order_id: str,
        side: Side,
        price: float,
        quantity: float,
        tif: TimeInForce = TimeInForce.GTC,
    ) -> Order:
        return Order(
            order_id=order_id,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            time_in_force=tif,
        )

    return _limit


def test_limit_buy_appears_in_bids_at_correct_price_level(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("buy-1", Side.BUY, 250.5, 6.0))
    snap = book.snapshot(depth=5)
    assert snap["bids"] == [{"price": 250.5, "qty": 6.0}]
    assert snap["asks"] == []
    assert book.best_bid() == (250.5, 6.0)


def test_limit_sell_appears_in_asks_at_correct_price_level(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("sell-1", Side.SELL, 251.25, 4.0))
    snap = book.snapshot(depth=5)
    assert snap["asks"] == [{"price": 251.25, "qty": 4.0}]
    assert snap["bids"] == []
    assert book.best_ask() == (251.25, 4.0)


def test_cancel_existing_order_returns_true_and_removes_from_book(
    book: OrderBook, limit_order
) -> None:
    oid = make_order_id()
    o = limit_order(oid, Side.SELL, 88.0, 5.0)
    book.submit(o)
    assert book.best_ask() == (88.0, 5.0)
    assert book.cancel_order(oid) is True
    assert o.status is Status.CANCELLED
    assert book.best_ask() is None
    assert book.snapshot(depth=5)["asks"] == []


def test_cancel_nonexistent_order_id_returns_false(book: OrderBook) -> None:
    assert book.cancel_order("does-not-exist") is False


def test_best_bid_and_best_ask_return_correct_price_qty_tuple(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("bid", Side.BUY, 42.0, 11.0))
    book.submit(limit_order("ask", Side.SELL, 44.0, 13.0))
    assert book.best_bid() == (42.0, 11.0)
    assert book.best_ask() == (44.0, 13.0)


def test_spread_returns_best_ask_minus_best_bid(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("b", Side.BUY, 99.0, 1.0))
    book.submit(limit_order("a", Side.SELL, 101.5, 1.0))
    assert book.spread() == 2.5


def test_snapshot_dict_shape_top_depth_levels_and_values(
    book: OrderBook, limit_order
) -> None:
    for p in (100.0, 99.0, 98.0, 97.0):
        book.submit(limit_order(f"bid-{p}", Side.BUY, p, 1.0))
    for p in (101.0, 102.0, 103.0, 104.0):
        book.submit(limit_order(f"ask-{p}", Side.SELL, p, 1.0))

    snap = book.snapshot(depth=2)
    assert isinstance(snap, dict)
    assert set(snap.keys()) == {"bids", "asks"}
    assert isinstance(snap["bids"], list)
    assert isinstance(snap["asks"], list)
    for row in snap["bids"] + snap["asks"]:
        assert set(row.keys()) == {"price", "qty"}
        assert isinstance(row["price"], float)
        assert isinstance(row["qty"], float)

    assert snap["bids"] == [
        {"price": 100.0, "qty": 1.0},
        {"price": 99.0, "qty": 1.0},
    ]
    assert snap["asks"] == [
        {"price": 101.0, "qty": 1.0},
        {"price": 102.0, "qty": 1.0},
    ]


def test_resting_bid_and_ask(book: OrderBook, limit_order) -> None:
    book.submit(limit_order("b1", Side.BUY, 99.0, 5.0))
    book.submit(limit_order("a1", Side.SELL, 101.0, 3.0))
    assert book.best_bid() == (99.0, 5.0)
    assert book.best_ask() == (101.0, 3.0)


def test_crossing_buy_matches_resting_sell(book: OrderBook, limit_order) -> None:
    book.submit(limit_order("a1", Side.SELL, 100.0, 4.0))
    trades = book.submit(limit_order("b1", Side.BUY, 100.0, 4.0))
    assert len(trades) == 1
    assert trades[0].price == 100.0
    assert trades[0].quantity == 4.0
    assert trades[0].aggressor_side is Side.BUY
    assert book.best_ask() is None


def test_partial_fill_and_rest(book: OrderBook, limit_order) -> None:
    book.submit(limit_order("a1", Side.SELL, 100.0, 10.0))
    trades = book.submit(limit_order("b1", Side.BUY, 100.0, 3.0))
    assert len(trades) == 1
    assert trades[0].quantity == 3.0
    assert book.best_ask() == (100.0, 7.0)


def test_cancel_order_idempotent_false_after_removal(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("rest", Side.SELL, 100.0, 5.0))
    assert book.cancel_order("rest") is True
    assert book.cancel_order("rest") is False


def test_filled_resting_not_in_cancel_registry(
    book: OrderBook, limit_order
) -> None:
    book.submit(limit_order("seller", Side.SELL, 10.0, 1.0))
    book.submit(limit_order("buyer", Side.BUY, 10.0, 1.0))
    assert book.cancel_order("seller") is False
    assert book.cancel_order("buyer") is False
