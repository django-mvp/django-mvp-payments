"""Rendering a minor-unit amount in its own currency (Article XVI)."""

from mvp_payments.money import Money


class TestMoney:
    """An amount is converted against its own currency's exponent, never assumed."""

    def test_a_two_decimal_currency_renders_with_two_decimal_places(self):
        assert str(Money(minor_units=2000, currency="USD")) == "20.00 USD"

    def test_a_zero_decimal_currency_renders_as_a_whole_number(self):
        assert str(Money(minor_units=2000, currency="JPY")) == "2,000 JPY"

    def test_a_three_decimal_currency_renders_with_three_decimal_places(self):
        assert str(Money(minor_units=2000, currency="BHD")) == "2.000 BHD"

    def test_an_amount_with_no_currency_renders_nothing(self):
        assert str(Money(minor_units=2000, currency="")) == ""

    def test_the_provider_records_a_currency_in_lower_case_and_it_still_converts(self):
        """The case the backend actually stores, which is not the case these sets hold.

        Stripe reports a currency as a lower-case ISO code and the backend writes the
        field through verbatim, so a real ``Price`` row holds ``"jpy"``, never ``"JPY"``.
        Read literally against an upper-case table, a zero-decimal amount comes out a
        hundred times too small and a three-decimal one ten times too large — on the
        page, to the person paying it.
        """
        assert str(Money(minor_units=2000, currency="jpy")) == "2,000 JPY"
        assert str(Money(minor_units=2000, currency="bhd")) == "2.000 BHD"
        assert str(Money(minor_units=2000, currency="usd")) == "20.00 USD"

    def test_a_currency_is_carried_in_the_case_it_is_written_in(self):
        assert Money(minor_units=2000, currency="jpy").currency == "JPY"
