// Runs billing_portal.js against a stubbed page, clicks its one control, and
// prints what happened as JSON: the token it sent, which messages it
// revealed, and where it sent the reader.
//
// Usage: node billing_portal_harness.js <path to billing_portal.js> '<scenario JSON>'
// Scenario: { cookie, renderedToken, status, redirected, body } for the control,
// or { refreshTo } for a page waiting on the provider, with no control on it.
const fs = require("fs");
const vm = require("vm");

const [scriptPath, scenarioJson] = process.argv.slice(2);
const scenario = JSON.parse(scenarioJson);

const element = () => ({ hidden: true });
const messages = {
  "[data-mvp-payments-portal-link-failure]": element(),
  "[data-mvp-payments-portal-link-stale]": scenario.noStaleMessage ? null : element(),
};
let clickHandler = null;
const button = { addEventListener: (_, handler) => { clickHandler = handler; } };
const link = {
  dataset: { endpoint: "/api/billing-portal/", csrfToken: scenario.renderedToken },
  querySelector: (selector) => (selector === "button" ? button : messages[selector] || null),
};

const notice = { dataset: { mvpPaymentsRefreshTo: scenario.refreshTo } };
const sent = {};
const timers = [];
const context = {
  document: {
    cookie: scenario.cookie || "",
    querySelectorAll: (selector) => {
      if (selector === "[data-mvp-payments-portal-link]") {
        return scenario.refreshTo ? [] : [link];
      }
      return scenario.refreshTo ? [notice] : [];
    },
  },
  window: {
    location: {
      href: "about:blank",
      replace(url) {
        this.href = url;
      },
    },
  },
  // Runs a timer at once, recording its delay, so a test never waits on it.
  setTimeout: (callback, delay) => {
    timers.push(delay);
    callback();
  },
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
if (clickHandler) clickHandler();

setTimeout(() => {
  console.log(
    JSON.stringify({
      token: sent.token,
      failureShown: !messages["[data-mvp-payments-portal-link-failure]"].hidden,
      staleShown: Boolean(
        messages["[data-mvp-payments-portal-link-stale]"] &&
          !messages["[data-mvp-payments-portal-link-stale]"].hidden
      ),
      location: context.window.location.href,
      timers,
    })
  );
}, 20);
