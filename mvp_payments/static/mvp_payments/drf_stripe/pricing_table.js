/**
 * Reveals <c-drf-stripe.pricing-table>'s hidden could-not-be-loaded message
 * wherever the provider's own custom element never registered — the only
 * signal available after load that its library did not arrive, since there
 * is no event to listen for (US-4 scenario 3, FR-010).
 *
 * A timing-based check — wait n milliseconds and see — was considered and
 * rejected (research.md): it is flaky, and it would misreport states this
 * package leaves entirely to the provider to render, such as an archived
 * table or a mismatched key pair.
 *
 * No build step and no bundler (Article XIII) — this file is loaded exactly
 * as the host project loads its other static assets, and states what it
 * needs by looking for its own marker rather than assuming one is present.
 */
window.addEventListener("load", () => {
  if (customElements.get("stripe-pricing-table")) return;

  document
    .querySelectorAll("[data-mvp-payments-pricing-table-unavailable]")
    .forEach((message) => {
      message.hidden = false;
    });
});
