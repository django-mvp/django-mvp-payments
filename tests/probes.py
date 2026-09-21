"""Running a probe in a process that starts with the settings it is testing.

Some of what this package guarantees is decided once, at a process's start:
the URL configuration is built when it is imported, and navigation entries are
registered when the application is ready. A project that never installed a
backend is a process that never installed it, and overriding a setting inside
a running test does not reproduce that — the state was already built.

A probe is therefore a short script run in a fresh interpreter under a chosen
settings module. It prints one line of JSON, which is what comes back here.

The exception is a guarantee that is decided live, while a page renders.
`tests/test_views.py::TestURLsNotMounted` overrides the URL configuration
in-process for exactly that reason, and says so.
"""

import json
import os
import subprocess
import sys


def run_probe(script: str, settings_module: str) -> dict:
    """Run `script` under `settings_module` and return the JSON it printed."""
    # sys.executable and a module-level string constant, no untrusted input.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        env={**os.environ, "DJANGO_SETTINGS_MODULE": settings_module},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])
