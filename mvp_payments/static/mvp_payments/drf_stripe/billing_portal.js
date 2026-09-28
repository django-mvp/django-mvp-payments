// Posts each portal-link control to its endpoint and follows the address returned,
// revealing the control's hidden failure message on any failure (ADR 0005).
// Loaded as a plain static file, with no build step (Article XII).
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
