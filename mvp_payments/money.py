"""Render a minor-unit amount in its own currency (Articles XIV and XV).

A provider reports an amount as an integer in a currency's minor unit, and not every currency
has two decimal places. The exponent is held here as a table rather than pulled from ``babel``
(ADR 0004).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from django.utils.formats import number_format


@dataclass(frozen=True)
class Money:
    """A minor-unit amount, rendered in its own currency or not at all.

    Attributes:
        minor_units: The amount in the currency's minor unit, as the provider reports it.
        currency: The ISO currency code, in any case. Empty when none is known.
        ZERO_DECIMAL: Currencies Stripe records with no fractional unit.
        THREE_DECIMAL: Currencies Stripe records to a thousandth of the unit.
    """

    minor_units: int
    currency: str = ""

    def __post_init__(self) -> None:
        """Hold the currency as the upper-case ISO code the exponent tables use.

        Stripe reports a lower-case code, which would otherwise fall through to two decimal
        places and render a zero-decimal amount a hundred times too small.
        """
        object.__setattr__(self, "currency", self.currency.upper())

    ZERO_DECIMAL: ClassVar[frozenset[str]] = frozenset(
        {
            "BIF",
            "CLP",
            "DJF",
            "GNF",
            "JPY",
            "KMF",
            "KRW",
            "MGA",
            "PYG",
            "RWF",
            "UGX",
            "VND",
            "VUV",
            "XAF",
            "XOF",
            "XPF",
        }
    )

    THREE_DECIMAL: ClassVar[frozenset[str]] = frozenset(
        {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
    )

    @property
    def exponent(self) -> int:
        """The number of places past the decimal point this currency's minor unit sits at."""
        if self.currency in self.ZERO_DECIMAL:
            return 0
        if self.currency in self.THREE_DECIMAL:
            return 3
        return 2

    @property
    def amount(self) -> Decimal:
        """This amount in the currency's own unit, rather than its minor unit."""
        return Decimal(self.minor_units) / Decimal(10**self.exponent)

    def __str__(self) -> str:
        """Format the amount under the active locale, followed by its currency code.

        Returns:
            The formatted amount, or an empty string without a currency rather than a
            guessed one (Article XV).
        """
        if not self.currency:
            return ""
        formatted = number_format(
            self.amount, decimal_pos=self.exponent, force_grouping=True
        )
        return f"{formatted} {self.currency}"
