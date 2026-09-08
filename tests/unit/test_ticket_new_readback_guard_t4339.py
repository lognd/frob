"""T-4339: `frob ticket new` printed its `created T-####: <title>` success
line BEFORE the ledger commit ran, and that commit step can itself
discard the just-written ticket on a `LandInProgress` timeout
(`commit_ticket_ledger_change`'s `rollback_on_land_in_progress=True`
path, `_rollback_pathspecs`, `git clean -fd` over the still-untracked
ticket path). One filed ticket (T-4313) hit exactly that window: the
success line printed, the rollback fired moments later, and the only
surviving trace was an orphaned `.frob/tickets/T-4313.lock` next to a
`tickets/T-4313/` directory that no longer existed.

These tests FORCE both failure seams directly (never by filing tickets
until one happens to fail, per T-4339's own verification requirement):

1. the commit step reporting `LandInProgress` (the seam T-4313 actually
   hit) -- asserts the command exits nonzero and prints NO success line
   in either the human or `--json` form.
2. a read-back miss for any OTHER reason (the general guard `_confirm_
   new_ticket_readback_or_exit` adds, independent of root cause) --
   same assertion, forced by making the post-commit `load_all` read-back
   report the id absent even though `new_ticket`/commit both reported
   success.

A third test confirms the ORDINARY path is unaffected: the success line
still prints, and it still reflects a ticket that genuinely reads back
from the store."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new
from frob.tickets._leases import LeaseError


# frob:ticket T-4339
def _cfg(tmp_path: Path, *, json_flag: bool = False) -> AppConfig:
    """A minimal `frob ticket new`-shaped `AppConfig` -- test helper only,
    mirroring `test_ticket_new_json.py`'s own precedent for calling `_new`
    directly against a bare `tmp_path`, no git repo required."""
    return AppConfig(
        ticket_command="new",
        ticket_title="T-4339 readback guard subject",
        ticket_body="## Description\nx\n",
        ticket_kind="bug",
        ticket_path=tmp_path,
        ticket_scope=["src/x.py"],
        ticket_ack_related=True,
        ticket_json=json_flag,
    )


# frob:ticket T-4339
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# test methods -- there is no production caller to wire it to by design" \
# permanent="true"
def _info_messages(caplog) -> list[str]:  # noqa: ANN001
    """Every INFO-level log message captured -- the channel both the
    human `created ...` line and the `--json` payload go out on."""
    return [r.message for r in caplog.records if r.levelno == logging.INFO]


# frob:ticket T-4339
class TestReadbackGuardForcesLoudFailure:
    """T-4339: the success line must follow a successful read-back, never
    precede the write -- forced here at both seams that can violate it."""

    # frob:tests \
    # tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFa\
    # ilure.test_land_in_progress_rollback_prints_no_success_line
    def test_land_in_progress_rollback_prints_no_success_line(
        self, tmp_path: Path, caplog, monkeypatch
    ) -> None:
        """FORCED CONDITION: the commit step reports `Err(LandInProgress)`
        -- the exact seam T-4313 hit (a concurrent land's rollback of the
        just-written, still-uncommitted ticket). Asserts `_new` exits
        nonzero and the `created <id>: ...` line was NEVER logged, human
        or JSON."""
        import frob.tickets._leases as leases_mod

        monkeypatch.setattr(
            leases_mod,
            "commit_ticket_ledger_change",
            lambda *a, **k: Err(LeaseError.LandInProgress),
        )

        with caplog.at_level(logging.INFO):
            with pytest.raises(SystemExit) as exc_info:
                _new(tmp_path, _cfg(tmp_path))

        assert exc_info.value.code == 1
        messages = _info_messages(caplog)
        assert not any(m.startswith("created ") for m in messages), (
            "success line must not print when the ledger commit reports "
            "LandInProgress -- the ticket was rolled back"
        )

    # frob:tests \
    # tests/unit/test_ticket_new_readback_guard_t4339.py::TestReadbackGuardForcesLoudFa\
    # ilure.test_readback_miss_after_reported_success_prints_no_success_line
    def test_readback_miss_after_reported_success_prints_no_success_line(
        self, tmp_path: Path, caplog, monkeypatch
    ) -> None:
        """FORCED CONDITION: `new_ticket` and the commit step both report
        `Ok`, but the read-back (`load_all`) that runs immediately after
        finds the id absent -- simulating any OTHER silent-loss seam, not
        just the LandInProgress rollback. Asserts `_new` exits nonzero
        and prints NO success line, even though every step up to the
        read-back reported success."""
        import sys

        # `frob.app.ticket_runner`'s package `__init__` re-exports `_new`
        # (the function) under the SAME name as this submodule, which
        # shadows `frob.app.ticket_runner._new` as an attribute lookup --
        # go through `sys.modules` directly to reach the real module.
        new_mod = sys.modules["frob.app.ticket_runner._new"]
        monkeypatch.setattr(
            new_mod,
            "_commit_new_ticket_ledger_change_or_exit",
            lambda root, ticket, no_commit: None,
        )
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "load_all", lambda root: Ok({}))

        with caplog.at_level(logging.INFO):
            with pytest.raises(SystemExit) as exc_info:
                _new(tmp_path, _cfg(tmp_path))

        assert exc_info.value.code == 1
        messages = _info_messages(caplog)
        assert not any(m.startswith("created ") for m in messages), (
            "success line must not print when the post-commit read-back "
            "cannot find the ticket, regardless of what reported success "
            "earlier"
        )


# frob:ticket T-4339
class TestNormalPathStillCommitsAndReportsSuccess:
    """The ordinary, uncontended path is unaffected by the guard: the
    success line still prints, and by then the ticket genuinely reads
    back from the store (this is what the guard checks, not a mock)."""

    # frob:tests \
    # tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAnd\
    # ReportsSuccess.test_ordinary_filing_prints_success_and_reads_back
    def test_ordinary_filing_prints_success_and_reads_back(
        self, tmp_path: Path, caplog
    ) -> None:
        """No mocking of the write/commit/read-back path at all: a plain
        filing must still print `created T-####: ...` (unchanged human
        output, T-4339 only reorders WHEN it prints, never whether)."""
        from frob.tickets import load_all

        with caplog.at_level(logging.INFO):
            _new(tmp_path, _cfg(tmp_path))

        messages = _info_messages(caplog)
        success = [m for m in messages if m.startswith("created T-")]
        assert success, "expected a created T-#### line on the normal path"
        assert "T-4339 readback guard subject" in success[-1]

        ticket_id = success[-1].split()[1].rstrip(":")
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert ticket_id in loaded.danger_ok, (
            "the ticket named in the success line must genuinely read "
            "back from the store"
        )

    # frob:tests \
    # tests/unit/test_ticket_new_readback_guard_t4339.py::TestNormalPathStillCommitsAnd\
    # ReportsSuccess.test_json_path_still_reports_success_and_reads_back
    def test_json_path_still_reports_success_and_reads_back(
        self, tmp_path: Path, caplog
    ) -> None:
        """Same guarantee for the `--json` output path (T-3308): still
        emits its payload, and the id it names still reads back."""
        from frob.tickets import load_all

        with caplog.at_level(logging.INFO):
            _new(tmp_path, _cfg(tmp_path, json_flag=True))

        messages = _info_messages(caplog)
        assert messages, "expected at least one INFO record"
        payload = json.loads(messages[-1])
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert payload["id"] in loaded.danger_ok
