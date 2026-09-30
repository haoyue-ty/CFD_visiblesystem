"""Pytest bootstrap for the independent QA assertion suite (Phase 5B, Window 4).

These tests are deliberately separated from ``tests/test_bootstrap.py``: that file
verifies the software bootstrap, this package verifies the *scientific* and
*contract* acceptance of the Case8 functional slice.

Marking policy
--------------
Every assertion that cannot yet pass because the production implementation has not
been merged is marked ``xfail`` with an explicit ``WAITING_FOR_IMPLEMENTATION`` or
``FOUND_FAILURE`` reason. ``strict=True`` is used for merge-readiness markers so an
unexpected pass is reported — the handoff must never overstate readiness. Genuine
defects found in this window use ``strict=False`` because by construction they are
expected to *fail* today and must start passing once the defect is fixed; that
transition is reported as CLEARED in the handoff.
"""

from __future__ import annotations

import pytest

from backend import create_app
from backend.core.settings import Settings


@pytest.fixture
def app():
    """Bootstrap application with no scientific adapter attached (baseline)."""
    application = create_app()
    application.config["TESTING"] = True
    return application


def make_case8_route_app(*, configure_catalog=None):
    """Build an app whose catalog is extended by Window 2's registration code.

    Kept here so QA assertions exercise the real catalog/routing/error machinery
    rather than a private reimplementation of it.
    """
    return create_app(Settings(), configure_catalog=configure_catalog)
