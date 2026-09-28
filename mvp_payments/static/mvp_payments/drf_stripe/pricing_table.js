// Reveals the pricing table's hidden could-not-be-loaded message when the provider's
// custom element never registered: there is no load event to listen for, and a timer
// would misreport states the provider renders itself (FS-003).
window.addEventListener("load", () => {
  if (customElements.get("stripe-pricing-table")) return;

  document
    .querySelectorAll("[data-mvp-payments-pricing-table-unavailable]")
    .forEach((message) => {
      message.hidden = false;
    });
});
