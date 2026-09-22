# Progress — 003 Offer plans through the provider's own pricing table

## 2026-09-22 — S3 PLAN

Picked off the feature queue as the only runnable feature across every registered repository.
Nothing had been delivered in this repository since the specification landed, so there was no
spec-against-spec comparison to make.

Branch `feat/003-pricing-table` off `origin/main` at `a73cbb1`, in a worktree of its own with the
commit identity bound to the repository's bot. Baseline verified green before anything was written:
lint, typecheck, test, build and conformance all passed on `a73cbb1`.

Read before planning:

- `drf_stripe/stripe_api/customers.py` at version 1.2.2 — the installed backend matches a provider
  customer to an application user on `customer.email` alone, confirming the assumption FR-005 rests
  on.
- The provider's published guide to the embeddable pricing table — the element's attribute list,
  and the fact that an undefined custom element renders as nothing with no event to listen for.

Both readings are recorded in `research.md`. The second settled how FR-010 is detected: one check
for whether the custom element is defined, which covers both the library never loading and the
provider's origin being unreachable, and nothing timing-based.

Plan written: one component, one view beside the one it mirrors, one static file, five stories in
priority order with no foundational phase, because this feature reads no record and needs nothing
seeded before the first story.

The plan carries one thing the specification anticipated: two sentences in the constitution forbid
reading a publishable key from settings anywhere in this package, and the shipped Plans page cannot
work under that reading. Both are narrowed to the component in US-5, with the reasoning left in
`decisions.md` where it already is.
