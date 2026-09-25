"""``billing_portal.js`` — the script behind "Manage subscription" and "Switch plans".

Run under Node against a stubbed page (``billing_portal_harness.js``), because the behaviour worth
testing is the script's: which security token it sends, and what it tells a reader when the
handoff is refused. Skipped where Node is not installed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "mvp_payments/static/mvp_payments/drf_stripe/billing_portal.js"
)
HARNESS = Path(__file__).with_name("billing_portal_harness.js")

NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node is needed to run the script")


def click(**scenario):
    """Load the script on a stubbed page, click its control, and report what it did."""
    # Every argument is fixed by this module or built from a test's own literals.
    result = subprocess.run(  # noqa: S603
        [NODE, str(HARNESS), str(SCRIPT), json.dumps(scenario)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class TestBillingPortalScript:
    def test_it_sends_the_current_cookie_token_rather_than_the_one_rendered(self):
        """Signing in again replaces the token, so the one on a page left open is refused.

        The cookie always holds the current one.
        """
        outcome = click(
            cookie="theme=dark; csrftoken=current-token",
            renderedToken="token-from-when-the-page-loaded",
            status=200,
            body={"url": "https://billing.example.com/session"},
        )

        assert outcome["token"] == "current-token"
        assert outcome["location"] == "https://billing.example.com/session"

    def test_without_the_cookie_it_sends_the_token_the_page_rendered(self):
        """A project keeping its token in the session, not a cookie, still works."""
        outcome = click(
            renderedToken="rendered-token",
            status=200,
            body={"url": "https://billing.example.com/session"},
        )

        assert outcome["token"] == "rendered-token"

    def test_a_refused_request_asks_the_reader_to_reload(self):
        outcome = click(renderedToken="stale", status=403)

        assert outcome["staleShown"] is True
        assert outcome["failureShown"] is False
        assert outcome["location"] == "about:blank"

    def test_being_sent_to_sign_in_asks_the_reader_to_reload(self):
        """Signed out since the page loaded: the endpoint redirects to the sign-in page."""
        outcome = click(renderedToken="stale", status=200, redirected=True)

        assert outcome["staleShown"] is True
        assert outcome["failureShown"] is False

    def test_any_other_failure_says_the_portal_could_not_be_reached(self):
        outcome = click(renderedToken="token", status=500)

        assert outcome["failureShown"] is True
        assert outcome["staleShown"] is False

    def test_markup_without_the_reload_message_falls_back_to_the_failure_message(
        self,
    ):
        """A project that wrote its own control before that message existed still hears why."""
        outcome = click(renderedToken="stale", status=403, noStaleMessage=True)

        assert outcome["failureShown"] is True

    def test_a_click_anywhere_else_on_the_page_does_nothing(self):
        outcome = click(renderedToken="token", status=200, clickOutside=True)

        assert outcome["posted"] is False
