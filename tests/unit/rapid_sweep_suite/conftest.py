"""Shared autouse fixture for the tests/unit/rapid_sweep_suite/ package
(T-3595 split of tests/unit/test_rapid_sweep.py): defaults the liveness-
gate subprocess spawn every family module relies on to refused."""

from __future__ import annotations

import pytest
from typani import Err

from frob.process._guard import ProcessGuardError


@pytest.fixture(autouse=True)
def _default_true_count_spawn_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-3222: `_file_regression_ticket` now spends its own independent
    `frob check --json` re-measure (`_reverify_unfiled_pairs_at_file_
    time`, via `_matching_error_diagnostics`/`guarded_subprocess_run`) as
    a FILING gate, not just a cosmetic count -- every test in this
    package that builds a fake `tmp_path` "repo" and expects a finding
    to still be filed would otherwise let that spawn run for REAL
    against a directory `frob check` cannot meaningfully scan, which
    (truthfully, but irrelevantly to what those tests are actually
    checking) reports every identity as vanished and breaks assertions
    that predate T-3222 by design, not by coincidence. Default this
    spawn to REFUSED (`ProcessGuardError.ExecDisabled`) for every test
    here -- the `matched is None` -> "unmeasurable, file everything
    unchanged" branch, i.e. exactly this package's pre-T-3222 behavior
    -- so tests exercising attribution/dedup/naming/dispose/close logic
    never need their own mock for this unrelated concern. Tests that
    specifically exercise the liveness gate (`TestReverifyUnfiledPairsAt
    FileTime`, and the two `TestFileRegressionTicket` tests naming
    T-3222) monkeypatch the same target again afterward, which wins over
    this default."""
    monkeypatch.setattr(
        "frob.process._guard.guarded_subprocess_run",
        lambda *a, **k: Err(ProcessGuardError.ExecDisabled),
    )
