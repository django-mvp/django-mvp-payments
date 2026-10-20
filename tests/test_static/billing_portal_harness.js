// Runs billing_portal.js against a stubbed page, clicks its one control, and
// prints what happened as JSON: the token it sent, which messages it
// revealed, and where it sent the reader.
//
// Usage: node billing_portal_harness.js <path to billing_portal.js> '<scenario JSON>'
// Scenario: { cookie, renderedToken, status, redirected, body, noStaleMessage,
//             clickOutside }
const fs = require("fs");
const vm = require("vm");

const [scriptPath, scenarioJson] = process.argv.slice(2);
const scenario = JSON.parse(scenarioJson);

const element = () => ({ hidden: true });
const messages = {
  "[data-mvp-payments-portal-link-failure]": element(),
  "[data-mvp-payments-portal-link-stale]": scenario.noStaleMessage ? null : element(),
};
const link = {
  dataset: { endpoint: "/api/billing-portal/", csrfToken: scenario.renderedToken },
  querySelector: (selector) => messages[selector] || null,
};
// What was clicked: the control's button, or something elsewhere on the page.
const target = {
  closest: (selector) => {
    if (scenario.clickOutside) return null;
    return selector === "[data-mvp-payments-portal-link]" ? link : {};
  },
};

let clickListener = null;
const sent = {};
const context = {
  document: {
    cookie: scenario.cookie || "",
    addEventListener: (type, listener) => {
      if (type === "click") clickListener = listener;
    },
  },
  window: { location: { href: "about:blank" } },
  fetch: (url, options) => {
    sent.url = url;
    sent.token = options.headers["X-CSRFToken"];
    return Promise.resolve({
      ok: scenario.status >= 200 && scenario.status < 300,
      status: scenario.status,
      redirected: Boolean(scenario.redirected),
      json: () =>
        scenario.body === undefined
          ? Promise.reject(new Error("not JSON"))
          : Promise.resolve(scenario.body),
    });
  },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(scriptPath, "utf8"), context);
clickListener({ target });

setTimeout(() => {
  const stale = messages["[data-mvp-payments-portal-link-stale]"];
  console.log(
    JSON.stringify({
      token: sent.token,
      posted: sent.url !== undefined,
      failureShown: !messages["[data-mvp-payments-portal-link-failure]"].hidden,
      staleShown: Boolean(stale && !stale.hidden),
      location: context.window.location.href,
    })
  );
}, 20);
