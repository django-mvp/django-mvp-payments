/**
 * Binds <c-drf-stripe.portal-link>'s control: posts to the backend's portal
 * endpoint, carrying the CSRF token the component rendered as data, and
 * follows the address the answer carries. Reveals the control's own hidden
 * failure message on any failure rather than sending the reader nowhere
 * (D3, US-2 scenario 3).
 *
 * No build step and no bundler (Article XIII) — this file is loaded exactly
 * as the host project loads its other static assets, and states what it
 * needs by looking for its own control rather than assuming one is present.
 */
document.querySelectorAll("[data-mvp-payments-portal-link]").forEach((link) => {
  const button = link.querySelector("button");
  const failure = link.querySelector("[data-mvp-payments-portal-link-failure]");
  const endpoint = link.dataset.endpoint;
  const csrfToken = link.dataset.csrfToken;

  button.addEventListener("click", () => {
    failure.hidden = true;

    fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken },
    })
      .then((response) => {
        if (!response.ok) throw new Error("billing portal request failed");
        return response.json();
      })
      .then((data) => {
        if (!data.url) throw new Error("billing portal response carried no url");
        window.location.href = data.url;
      })
      .catch(() => {
        failure.hidden = false;
      });
  });
});
