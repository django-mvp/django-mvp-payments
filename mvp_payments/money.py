"""Rendering a minor-unit amount in its own currency (Article XVI, Article XV plumbing).

A provider reports an amount as an integer in a currency's minor unit — Stripe's ``2000`` is
£20.00 — and most currencies use two decimal places, but not all of them: a zero-decimal currency
such as JPY would be shown one hundred times too large by that assumption, and a three-decimal one
such as BHD one tenth too small. The exponent is held here, as a table, rather than pulled from
``babel``: that is a runtime dependency with a data bundle of its own, added for twenty-three
currency codes this module can state directly (Article VII, `research.md`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from django.utils.formats import number_format


@dataclass(frozen=True)
class Money:
    """A minor-unit amount, rendered in its own currency or not at all."""

    minor_units: int
    currency: str = ""

    def __post_init__(self) -> None:
        """Hold the currency as the upper-case ISO code, whatever case it arrived in.

        Stripe reports a currency as a lower-case code and the backend stores that field
        verbatim, so a real record holds ``"jpy"``. The tables below are written in the
        case the standard defines, and a lower-case code read against them silently falls
        through to two decimal places — which renders a zero-decimal amount a hundred
        times too small, on the page, to the person paying it.
        """
        object.__setattr__(self, "currency", self.currency.upper())

    #: Currencies Stripe records with no fractional unit: the amount recorded is already a whole
    #: number of the currency, not a multiple of one hundred.
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

    #: Currencies Stripe records to a thousandth of the unit rather than a hundredth.
    THREE_DECIMAL: ClassVar[frozenset[str]] = frozenset(
        {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
    )

    @property
    def exponent(self) -> int:
        """How many places past the decimal point this currency's minor unit sits at."""
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
        """The amount under the active locale, followed by its currency code.

        Renders nothing without a currency (Article XVI) — a component that received a bare
        integer has nothing honest to show, and guessing a currency would be worse than showing
        nothing.
        """
        if not self.currency:
            return ""
        formatted = number_format(
            self.amount, decimal_pos=self.exponent, force_grouping=True
        )
        return f"{formatted} {self.currency}"
