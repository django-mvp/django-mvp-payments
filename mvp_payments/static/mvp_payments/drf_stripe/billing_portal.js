/**
 * Binds <c-drf-stripe.portal-link>'s control, and the "Switch plans" control
 * <c-drf-stripe.plans-link> renders for a subscriber: posts to the endpoint
 * the control carries, with the CSRF token the component rendered as data,
 * and follows the address the answer carries. Reveals one of the control's own
 * hidden messages on any failure rather than sending the reader nowhere
 * (D3, US-2 scenario 3): "reload the page" when the page has outlived the
 * session, "could not be reached" otherwise.
 *
 * Also reloads the subscription page while <c-drf-stripe.provider-return> is
 * waiting for a payment to reach the backend, to the address it names.
 *
 * No build step and no bundler (Article XIII) — this file is loaded exactly
 * as the host project loads its other static assets, and states what it
 * needs by looking for its own control rather than assuming one is present.
 */
// The token Django checks is the one in its cookie now, not the one the page
// was rendered with: signing in again replaces it, so a page left open would
// send a token that is refused. The rendered one is the fallback for a
// project that keeps its token in the session instead of a cookie.
function currentCsrfToken(fallback) {
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : fallback;
}

document.querySelectorAll("[data-mvp-payments-portal-link]").forEach((link) => {
  const button = link.querySelector("button");
  const failure = link.querySelector("[data-mvp-payments-portal-link-failure]");
  const stale = link.querySelector("[data-mvp-payments-portal-link-stale]");
  const endpoint = link.dataset.endpoint;

  button.addEventListener("click", () => {
    failure.hidden = true;
    // Absent from markup a project wrote before this message existed.
    if (stale) stale.hidden = true;

    fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": currentCsrfToken(link.dataset.csrfToken) },
    })
      .then((response) => {
        // Refused, or sent to sign in: the page is older than the session,
        // and reloading it is what helps.
        if (stale && (response.status === 403 || response.redirected)) {
          stale.hidden = false;
          return null;
        }
        if (!response.ok) throw new Error("billing portal request failed");
        return response.json();
      })
      .then((data) => {
        if (data === null) return;
        if (!data.url) throw new Error("billing portal response carried no url");
        window.location.href = data.url;
      })
      .catch(() => {
        failure.hidden = false;
      });
  });
});

// Back from the provider with nothing current to show yet: the page names the
// address to reload to, and reloads until the backend has caught up or the
// view stops naming one.
document.querySelectorAll("[data-mvp-payments-refresh-to]").forEach((notice) => {
  setTimeout(() => {
    window.location.replace(notice.dataset.mvpPaymentsRefreshTo);
  }, 3000);
});
