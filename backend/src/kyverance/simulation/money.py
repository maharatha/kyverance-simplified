"""Fixed-decimal money helpers — never use float for cash or quantity amounts."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

MONEY_SCALE = Decimal("0.0001")
MONEY_QUANTIZE = Decimal("0.0001")
QTY_QUANTIZE = Decimal("0.0000000001")


def money(value: Decimal | str | int) -> Decimal:
    """Normalize a cash amount to DECIMAL(19,4) scale with banker's rounding."""
    if type(value) is float:
        raise TypeError("float is not allowed for money amounts")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid money amount: {value!r}") from exc
    return amount.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_EVEN)


def money_str(value: Decimal | str | int) -> str:
    """Serialize a money amount as a fixed-scale decimal string."""
    return format(money(value), "f")


def qty(value: Decimal | str | int) -> Decimal:
    """Normalize a share quantity to DECIMAL(28,10) scale."""
    if type(value) is float:
        raise TypeError("float is not allowed for quantity amounts")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid quantity: {value!r}") from exc
    return amount.quantize(QTY_QUANTIZE, rounding=ROUND_HALF_EVEN)


def qty_str(value: Decimal | str | int) -> str:
    """Serialize a quantity as a fixed-scale decimal string."""
    return format(qty(value), "f")
