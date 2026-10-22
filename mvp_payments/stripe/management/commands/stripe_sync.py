"""Bring the recorded customers' subscriptions into step with Stripe."""

from __future__ import annotations

import stripe
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from mvp_payments.stripe.models import Customer


class Command(BaseCommand):
    """Re-sync every recorded customer from Stripe, for when webhooks were missed."""

    help = "Bring every recorded Stripe customer's subscriptions into step with Stripe."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add the option that limits the run to one user.

        Args:
            parser: The parser to add the option to.
        """
        user_model = get_user_model()
        parser.add_argument(
            "--user",
            help=f"Sync only this user's customer, named by their {user_model.USERNAME_FIELD}.",
        )

    def handle(self, *args, **options) -> None:
        """Sync each customer in turn, each in its own transaction.

        Args:
            *args: Ignored.
            **options: The parsed options.

        Raises:
            CommandError: When the named user does not exist or has no customer, or when
                Stripe could not be asked. Customers already synced stay synced.
        """
        customers = Customer.objects.order_by("pk")
        username = options["user"]
        if username is not None:
            user_model = get_user_model()
            user = user_model._default_manager.filter(
                **{user_model.USERNAME_FIELD: username}
            ).first()
            if user is None:
                raise CommandError(_("No user %(name)s.") % {"name": username})
            customers = customers.filter(user=user)
            if not customers.exists():
                raise CommandError(
                    _("User %(name)s has no Stripe customer.") % {"name": username}
                )

        synced = 0
        for customer in customers:
            try:
                customer.sync()
            except stripe.StripeError as error:
                # Only the type: Stripe's message can echo part of the secret key.
                raise CommandError(
                    ngettext(
                        "Stripe could not be asked (%(error)s) after syncing %(count)d customer. "
                        "Run the command again to finish the rest.",
                        "Stripe could not be asked (%(error)s) after syncing %(count)d customers. "
                        "Run the command again to finish the rest.",
                        synced,
                    )
                    % {"error": type(error).__name__, "count": synced}
                ) from error
            synced += 1
        self.stdout.write(
            ngettext(
                "Synced %(count)d customer.",
                "Synced %(count)d customers.",
                synced,
            )
            % {"count": synced}
        )
