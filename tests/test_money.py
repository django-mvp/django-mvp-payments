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
