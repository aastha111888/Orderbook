from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto


class Side(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    LIMIT = auto()
    MARKET = auto()


class TimeInForce(Enum):
    GTC = auto()
    IOC = auto()
    FOK = auto()


class Status(Enum):
    OPEN = auto()
    PARTIAL = auto()
    FILLED = auto()
    CANCELLED = auto()


@dataclass
class Order:
    order_id: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float | None = None
    filled_qty: float = 0.0
    timestamp: float = field(default_factory=time.time)
    time_in_force: TimeInForce = TimeInForce.GTC
    status: Status = Status.OPEN
    trader_id: str | None = None
    symbol: str = "DEFAULT"

    @property
    def remaining_qty(self) -> float:
        return self.quantity - self.filled_qty

    @property
    def is_active(self) -> bool:
        return self.status in (Status.OPEN, Status.PARTIAL)


def make_order_id() -> str:
    return uuid.uuid4().hex[:8]
