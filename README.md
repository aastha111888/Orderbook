# Order Book Engine

A price-time priority limit order book engine built in Python, with a live terminal UI for submitting orders and watching the book update in real time. It includes a full matching engine that supports **limit** and **market** orders, plus **IOC** and **FOK** time-in-force behavior.

## Features

- Price-time priority matching engine
- Limit, market, IOC, and FOK order types
- O(log n) order insertion and cancellation
- Real-time terminal UI with live bid/ask ladder and trade blotter
- 26 unit tests with 100% pass rate

## Project Structure

```
Orderbook/
├── order_book/
│   ├── __init__.py      — Public exports for the package
│   ├── models.py        — Order dataclass and enums
│   ├── book.py          — OrderBook matching engine
│   └── trade.py         — Trade dataclass
├── tests/
│   ├── __init__.py      — Test package marker
│   ├── test_models.py   — Unit tests for Order model
│   └── test_book.py     — Unit tests for OrderBook
├── main.py              — Interactive terminal UI
├── requirements.txt     — Python dependencies
└── README.md            — Project documentation
```

## Getting Started

### Prerequisites

Python 3.11+

### Installation

```bash
git clone <YOUR_REPO_URL>
cd Orderbook
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python main.py
```

Run from the project root with `PYTHONPATH=.` if `order_book` is not installed as a package (e.g. `PYTHONPATH=. python main.py`).

## Order Syntax

Commands are case-insensitive. Type a line and press Enter in the terminal UI.

| Command   | Example |
| --------- | ------- |
| BUY LIMIT | `BUY LIMIT 100.0 x 5` |
| SELL LIMIT | `SELL LIMIT 99.0 x 3 IOC` |
| BUY MARKET | `BUY MARKET x 4` |
| SELL MARKET | `SELL MARKET x 2 FOK` |
| CANCEL | `CANCEL <order_id>` |
| QUIT | `QUIT` or `EXIT` |

## Tech Stack

Python, sortedcontainers, rich, pytest
