from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from order_book.models import Side


@dataclass(kw_only=True)
class Trade:
    trade_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    symbol: str
    price: float
    quantity: float
    aggressor_order_id: str
    passive_order_id: str
    aggressor_side: Side
    timestamp: float = field(default_factory=time.time)
