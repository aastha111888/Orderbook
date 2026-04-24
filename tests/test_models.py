import time

import pytest

from order_book.models import (
    Order,
    OrderType,
    Side,
    Status,
    TimeInForce,
    make_order_id,
)


@pytest.fixture
def make_order():
    def _make(
        *,
        order_id: str = "o1",
        side: Side = Side.BUY,
        quantity: float = 10.0,
        filled_qty: float = 0.0,
        status: Status = Status.OPEN,
        price: float = 100.0,
    ) -> Order:
        return Order(
            order_id=order_id,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            filled_qty=filled_qty,
            time_in_force=TimeInForce.GTC,
            status=status,
        )

    return _make


def test_remaining_qty_equals_quantity_minus_filled_qty(make_order) -> None:
    o = make_order(quantity=10.0, filled_qty=3.25)
    assert o.remaining_qty == o.quantity - o.filled_qty
    assert o.remaining_qty == 6.75


@pytest.mark.parametrize(
    "status,expected_active",
    [
        (Status.OPEN, True),
        (Status.PARTIAL, True),
        (Status.FILLED, False),
        (Status.CANCELLED, False),
    ],
)
def test_order_is_active_for_open_and_partial_only(
    make_order, status: Status, expected_active: bool
) -> None:
    o = make_order(status=status)
    assert o.is_active is expected_active


def test_two_orders_back_to_back_have_distinct_order_ids_from_make_order_id() -> None:
    o1 = Order(
        order_id=make_order_id(),
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=1.0,
        time_in_force=TimeInForce.GTC,
    )
    o2 = Order(
        order_id=make_order_id(),
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        quantity=2.0,
        price=2.0,
        time_in_force=TimeInForce.GTC,
    )
    assert o1.order_id != o2.order_id
    assert len(o1.order_id) == len(o2.order_id) == 8


def test_order_default_timestamp_is_recent_epoch_seconds() -> None:
    before = time.time()
    o = Order(
        order_id="1",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=1.0,
        time_in_force=TimeInForce.GTC,
    )
    after = time.time()
    assert before <= o.timestamp <= after
