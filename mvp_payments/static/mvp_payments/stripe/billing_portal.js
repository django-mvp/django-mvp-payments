// Posts each portal-link control to its endpoint and follows the address returned,
// revealing the control's hidden failure message on any failure (ADR 0005), or its
// "reload" message when the page has outlived the session.
// Loaded as a plain static file, with no build step (Article XII).

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

// One listener on the document rather than one per control, so a control
// swapped in later still works: the subscription region replaces itself when
// it polls for a payment that has just been made.
document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-mvp-payments-portal-link]");
  if (!link || !event.target.closest("button")) return;

  const failure = link.querySelector("[data-mvp-payments-portal-link-failure]");
  const stale = link.querySelector("[data-mvp-payments-portal-link-stale]");

  failure.hidden = true;
  // Absent from markup a project wrote before this message existed.
  if (stale) stale.hidden = true;

  fetch(link.dataset.endpoint, {
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
