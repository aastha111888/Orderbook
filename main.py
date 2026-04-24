"""Rich TUI harness: run from repo root with `python main.py`."""

import re
import threading
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from order_book.book import OrderBook
from order_book.models import Order, OrderType, Side, TimeInForce, make_order_id


def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="top", ratio=60),
        Layout(name="bottom", ratio=40),
    )
    layout["bottom"].split_row(
        Layout(name="trades", ratio=50),
        Layout(name="input", ratio=50),
    )
    return layout


def render_book(book: OrderBook, depth: int = 8) -> Table:
    snap = book.snapshot(depth=depth)
    bids = snap.get("bids", [])
    asks = snap.get("asks", [])

    table = Table(title="Order Book", expand=True)
    table.add_column("Bid Qty", justify="right", style="green")
    table.add_column("Bid Px", justify="right", style="green")
    table.add_column("Ask Px", justify="right", style="red")
    table.add_column("Ask Qty", justify="right", style="red")

    for i in range(depth):
        b = bids[i] if i < len(bids) else None
        a = asks[i] if i < len(asks) else None
        b_qty = "" if b is None else f"{b['qty']:.4g}"
        b_px = "" if b is None else f"{b['price']:.4g}"
        a_px = "" if a is None else f"{a['price']:.4g}"
        a_qty = "" if a is None else f"{a['qty']:.4g}"
        table.add_row(b_qty, b_px, a_px, a_qty)

    return table


def render_trades(trades: list) -> Table:
    table = Table(title="Recent Trades", expand=True)
    table.add_column("Time")
    table.add_column("Side")
    table.add_column("Price", justify="right")
    table.add_column("Qty", justify="right")

    for t in reversed(trades[-8:]):
        ts = time.strftime("%H:%M:%S", time.localtime(getattr(t, "timestamp", 0.0)))
        side = getattr(t, "aggressor_side", None)
        side_label = getattr(side, "name", "")
        side_style = "green" if side_label == "BUY" else "red" if side_label == "SELL" else ""
        table.add_row(
            ts,
            f"[{side_style}]{side_label}[/{side_style}]" if side_style else side_label,
            f"{t.price:.4g}",
            f"{t.quantity:.4g}",
        )

    return table


_ORDER_RE = re.compile(
    r"^\s*(BUY|SELL)\s+(LIMIT|MARKET)\s+"
    r"(?:(?P<price>\d+(?:\.\d+)?)\s+)?x\s*(?P<qty>\d+(?:\.\d+)?)\s*"
    r"(?P<tif>GTC|IOC|FOK)?\s*$",
    re.IGNORECASE,
)
_CANCEL_RE = re.compile(r"^\s*CANCEL\s+(?P<oid>\S+)\s*$", re.IGNORECASE)


def _parse_line(line: str):
    s = line.strip()
    if not s:
        return None
    up = s.upper()
    if up in {"QUIT", "EXIT"}:
        return ("quit",)

    m = _CANCEL_RE.match(s)
    if m:
        return ("cancel", m.group("oid"))

    m = _ORDER_RE.match(s)
    if not m:
        raise ValueError("Could not parse line")

    side_s = m.group(1).upper()
    typ_s = m.group(2).upper()
    qty = float(m.group("qty"))
    price_str = m.group("price")
    tif_s = (m.group("tif") or "GTC").upper()

    side = Side.BUY if side_s == "BUY" else Side.SELL
    tif = getattr(TimeInForce, tif_s)
    if typ_s == "LIMIT":
        if price_str is None:
            raise ValueError("LIMIT orders require a price")
        return ("order", side, OrderType.LIMIT, float(price_str), qty, tif)
    # MARKET
    if price_str is not None:
        raise ValueError("MARKET orders must not include a price")
    return ("order", side, OrderType.MARKET, None, qty, tif)


def _order_summary(o: Order) -> str:
    side = o.side.name
    typ = o.order_type.name
    qty = f"{o.quantity:g}"
    if o.order_type is OrderType.LIMIT:
        px = "" if o.price is None else f"{o.price:g} "
        return f"{side} {typ} {px}x {qty}"
    return f"{side} {typ} x {qty}"


def main() -> None:
    book = OrderBook()
    trades: list = []
    last_status: str = "Last: (none)"

    book_lock = threading.Lock()
    trades_lock = threading.Lock()
    update_cv = threading.Condition()
    stop_event = threading.Event()

    with book_lock:
        for px, qty in [(99.0, 10.0), (98.5, 5.0), (98.0, 8.0), (97.5, 3.0)]:
            book.submit(
                Order(
                    order_id=make_order_id(),
                    side=Side.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=qty,
                    price=px,
                    time_in_force=TimeInForce.GTC,
                )
            )
        for px, qty in [(101.0, 6.0), (101.5, 4.0), (102.0, 9.0), (102.5, 2.0)]:
            book.submit(
                Order(
                    order_id=make_order_id(),
                    side=Side.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=qty,
                    price=px,
                    time_in_force=TimeInForce.GTC,
                )
            )

    console = Console()
    layout = make_layout()

    def input_loop() -> None:
        nonlocal last_status
        while not stop_event.is_set():
            try:
                line = input().strip()
            except EOFError:
                stop_event.set()
                with update_cv:
                    update_cv.notify_all()
                return

            try:
                parsed = _parse_line(line)
                if parsed is None:
                    continue
                if parsed[0] == "quit":
                    stop_event.set()
                    with update_cv:
                        update_cv.notify_all()
                    return
                if parsed[0] == "cancel":
                    oid = parsed[1]
                    with book_lock:
                        ok = book.cancel_order(oid)
                    last_status = f"Last: CANCEL {oid} → {'OK' if ok else 'NOT FOUND'}"
                    with update_cv:
                        update_cv.notify_all()
                    continue

                _, side, otype, price, qty, tif = parsed
                order = Order(
                    order_id=make_order_id(),
                    side=side,
                    order_type=otype,
                    quantity=qty,
                    price=price,
                    time_in_force=tif,
                )
                with book_lock:
                    new_trades = book.submit(order)
                if new_trades:
                    with trades_lock:
                        trades.extend(new_trades)
                last_status = f"Last: {_order_summary(order)} → {order.status.name}"
                with update_cv:
                    update_cv.notify_all()
            except Exception as e:  # noqa: BLE001 - interactive loop
                print(f"Error: {e}")
                continue

    t = threading.Thread(target=input_loop, name="order-input", daemon=True)
    t.start()

    with Live(layout, console=console, refresh_per_second=12, screen=True):
        while not stop_event.is_set():
            with book_lock:
                book_table = render_book(book, depth=8)
            with trades_lock:
                trades_table = render_trades(trades)

            input_text = (
                "Enter orders:\n"
                "- BUY LIMIT 100.0 x 5\n"
                "- SELL LIMIT 99.0 x 3 IOC\n"
                "- BUY MARKET x 4\n"
                "- SELL MARKET x 2 FOK\n"
                "- CANCEL <order_id>\n"
                "- QUIT / EXIT\n\n"
                f"{last_status}\n"
            )

            layout["top"].update(Panel(book_table, title="book"))
            layout["trades"].update(Panel(trades_table, title="trades"))
            layout["input"].update(Panel(input_text, title="input"))

            with update_cv:
                update_cv.wait(timeout=0.25)


if __name__ == "__main__":
    main()
