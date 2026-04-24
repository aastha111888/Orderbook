"""Manual test harness: run from repo root with `python main.py`."""

from order_book import Order, OrderBook, OrderType, Side, TimeInForce


def main() -> None:
    book = OrderBook()
    book.submit(
        Order(
            order_id="seller-1",
            side=Side.SELL,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=5000.0,
            time_in_force=TimeInForce.GTC,
        )
    )
    book.submit(
        Order(
            order_id="buyer-1",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            quantity=50.0,
            price=4900.0,
            time_in_force=TimeInForce.GTC,
        )
    )
    print("After resting orders:", book.best_bid(), book.best_ask())

    trades = book.submit(
        Order(
            order_id="buyer-2",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            quantity=30.0,
            price=5000.0,
            time_in_force=TimeInForce.GTC,
        )
    )
    print("Trades:", trades)
    print("Best bid/ask after aggressive buy:", book.best_bid(), book.best_ask())


if __name__ == "__main__":
    main()
