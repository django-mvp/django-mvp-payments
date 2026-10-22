# Progress — FS-004

- 2026-10-22 Specification approved by Sam in session. Branch brought up to date with main (django-mvp 0.30.0). Research, plan and tasks written.

## 2026-10-22T08:43:03Z · Implementer US1 · T001

Did: added the stripe-lite extra (stripe>=16,<17) and moved the dev group onto it; uv sync moved the venv from stripe 7.14 to 16.0.0. The demo no longer mounts drf_stripe.urls and pins the global stripe.api_version to 2020-08-27 in DemoConfig.ready(). tests/test_app.py rewritten: interface rules now skip mvp_payments/stripe/, import scan uses ast, base requirements and the extra's requirements are asserted, and no module outside the app imports the SDK.
Verified: uv run pytest tests/test_app.py tests/test_demo.py (48 passed). New tests were red first (extra missing; demo URLconf import error on stripe.error; api_version unpinned).
Next: T002 app skeleton; the mypy_path check needs mvp_payments/stripe/ to exist, so it is done there.
Watch: deptry DEP002 would flag stripe until the app imports it, so it is ignored temporarily in pyproject.toml; T002 removes the ignore.
