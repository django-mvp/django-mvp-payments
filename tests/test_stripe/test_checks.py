"""The system checks that tell a developer which Stripe setting is missing."""

import pytest
from django.core.checks import run_checks

SECRET = "sk_test_a_secret_value_that_must_not_be_printed"
WEBHOOK = "whsec_a_secret_value_that_must_not_be_printed"


def stripe_findings():
    return [
        finding
        for finding in run_checks()
        if finding.id.startswith("mvp_payments_stripe.")
    ]


class TestSettingsChecks:
    def test_complete_settings_raise_nothing(self, settings):
        settings.MVP_PAYMENTS = {
            "STRIPE_SECRET_KEY": SECRET,
            "STRIPE_WEBHOOK_SECRET": WEBHOOK,
        }

        assert stripe_findings() == []

    @pytest.mark.parametrize(
        ("present", "missing", "error_id"),
        [
            ("STRIPE_WEBHOOK_SECRET", "STRIPE_SECRET_KEY", "mvp_payments_stripe.E001"),
            ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "mvp_payments_stripe.E002"),
        ],
    )
    def test_each_missing_setting_has_its_own_error_naming_it(
        self, settings, present, missing, error_id
    ):
        settings.MVP_PAYMENTS = {present: SECRET}

        findings = stripe_findings()

        assert [finding.id for finding in findings] == [error_id]
        assert missing in findings[0].msg

    @pytest.mark.parametrize("value", ["", None])
    def test_an_empty_setting_counts_as_missing(self, settings, value):
        settings.MVP_PAYMENTS = {
            "STRIPE_SECRET_KEY": value,
            "STRIPE_WEBHOOK_SECRET": WEBHOOK,
        }

        assert [finding.id for finding in stripe_findings()] == [
            "mvp_payments_stripe.E001"
        ]

    def test_both_missing_raises_both_errors(self, settings):
        settings.MVP_PAYMENTS = {}

        assert sorted(finding.id for finding in stripe_findings()) == [
            "mvp_payments_stripe.E001",
            "mvp_payments_stripe.E002",
        ]

    def test_no_mvp_payments_setting_at_all_raises_both_errors(self, settings):
        del settings.MVP_PAYMENTS

        assert len(stripe_findings()) == 2

    def test_a_message_names_no_configured_value(self, settings):
        settings.MVP_PAYMENTS = {"STRIPE_SECRET_KEY": SECRET}

        text = " ".join(
            f"{finding.msg} {finding.hint}" for finding in stripe_findings()
        )

        assert SECRET not in text
        assert WEBHOOK not in text
