# ADR 0004 — A currency's minor-unit exponent is a table in this package, not a dependency

**Status:** accepted

## Decision

`Money` holds the set of currencies the provider records with no fractional unit and the set it
records to a thousandth, and derives the exponent from them. `babel` was considered as the source
for that information and rejected.

## Why

A provider reports an amount as an integer in the currency's minor unit, so rendering it needs to
know where the decimal point goes. Assuming two places is wrong in both directions: a
zero-decimal currency shows a hundred times too large, a three-decimal one ten times too small.

`babel` knows all of it, and also brings a localised currency pattern. It is a runtime dependency
with a data bundle attached, added for twenty-three currency codes this package states in a dozen
lines. The constitution asks for a justification before a dependency is added and there is not one
here.

The consequence, accepted with it: an amount renders as a localised number beside its currency
code rather than as a symbol inside the locale's own pattern. A project that wants the symbol has
the `Decimal` and the code and can format them itself.

Converting minor units for display is not the calculation the specification forbids. That
prohibition is about producing a figure the backend never recorded — a total, a proration, a
conversion between currencies. Moving a decimal point renders the figure it did record.

## Revisit if

The package needs a currency symbol, a locale-specific currency pattern, or anything else `babel`
holds, at which point one dependency replaces several partial tables.
