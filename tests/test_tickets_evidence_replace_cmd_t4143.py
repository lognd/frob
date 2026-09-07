"""T-4143: `frob ticket evidence <id> --replace OLD NEW` accepting a
command-shaped (`cmd:`) `NEW` target, verified through its own
`reverify_cmd_evidence` channel instead of pytest resolution.

Kept in its own file, deliberately separate from
`tests/test_tickets_evidence_cli.py::TestReplaceEvidence` (T-4143's own
scope originally pointed at that shared file, but T-3936 -- an unrelated,
still-open Windows CI ticket -- had already claimed that entire file as
its own declared scope; landing a change there too would have silently
shipped T-3936's work ahead of its own close, the exact CrossTicketLeakage
guard this repo's `frob ticket land` refuses on). A second, small,
self-contained seed helper duplicates
`TestReplaceEvidence._seed_ticket`'s shape rather than importing across
files for one fixture, which is the more common pattern this test suite
already uses (see `tests/test_tickets_evidence_removal.py`'s own
`_seed_docs_ticket`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _new
from frob.testing._models import CollectedTests
from frob.tickets import TicketError, add_cmd_evidence, replace_evidence


def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, so this seed stays hermetic."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `_verify_ids_passing` report every id it is asked about as
    passing, without spawning pytest/cargo."""
    import frob.app.ticket_runner as runner_mod
    from frob.app.ticket_runner._verify import VerifyOutcome as _VerifyOutcome
    from frob.app.ticket_runner._verify import VerifyStatus as _VerifyStatus

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: {
            n: _VerifyOutcome(status=_VerifyStatus.PASSED) for n in node_ids
        },
    )


def _seed_feature_ticket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create T-0001, a feature-kind ticket carrying one pytest evidence
    id, and return its id."""
    _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
    _patch_passing(monkeypatch)
    cfg = AppConfig(
        ticket_command="new",
        ticket_title="replace evidence target",
        ticket_kind="feature",
        ticket_path=tmp_path,
        ticket_evidence_ids=["tests/x.py::test_old"],
    )
    _new(tmp_path, cfg)
    return "T-0001"


def _seed_docs_ticket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create T-0001, a docs-kind ticket carrying one pytest evidence id --
    `add_cmd_evidence` is kind-gated (docs/ux only, or a scope with no
    Python file), so a `cmd:` entry needs this rather than the plain
    feature-kind seed."""
    _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
    _patch_passing(monkeypatch)
    cfg = AppConfig(
        ticket_command="new",
        ticket_title="replace evidence cmd target",
        ticket_kind="docs",
        ticket_path=tmp_path,
        ticket_evidence_ids=["tests/x.py::test_old"],
    )
    _new(tmp_path, cfg)
    return "T-0001"


class TestReplaceEvidenceCmdTarget:
    """`replace_evidence` accepting a `cmd:`-shaped `new_node` (T-4143)."""

    def test_replace_target_may_be_a_reproducing_cmd_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_evidence_replace_cmd_t4143.py::TestReplaceEvidenceCmdTarget.test_replace_target_may_be_a_reproducing_cmd_entry  # noqa: E501
        # T-4143: `--replace`'s target validation is pytest-shaped
        # (resolve against `collected`, check against `passed`) -- a
        # `cmd:` entry can never appear in either set no matter how
        # genuine it is, so it was refused outright before this fix. The
        # correct check for a cmd: target is its OWN verification channel
        # (`reverify_cmd_evidence`: re-run the command, confirm it still
        # reproduces), not pytest resolution -- this proves that channel
        # is now actually consulted, not merely skipped.
        ticket_id = _seed_docs_ticket(tmp_path, monkeypatch)
        recorded = add_cmd_evidence(tmp_path, ticket_id, "printf ok")
        assert recorded.is_ok
        cmd_entry = recorded.danger_ok.evidence[-1]

        result = replace_evidence(
            tmp_path,
            ticket_id,
            "tests/x.py::test_old",
            cmd_entry,
            reason="pytest coverage replaced by a reproducing cmd: probe",
        )
        assert result.is_ok
        assert result.danger_ok.evidence == (cmd_entry,)

    def test_replace_target_cmd_entry_that_no_longer_reproduces_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_evidence_replace_cmd_t4143.py::TestReplaceEvidenceCmdTarget.test_replace_target_cmd_entry_that_no_longer_reproduces_is_rejected  # noqa: E501
        # T-4143: accepting a cmd: replacement target must still refuse a
        # false claim -- a hand-typed `cmd:` string whose recorded digest
        # does not match what the command ACTUALLY produces now is
        # exactly the false-evidence shape this whole family exists to
        # keep out, whether it arrives via `add_evidence` or `--replace`.
        ticket_id = _seed_feature_ticket(tmp_path, monkeypatch)
        fabricated = "cmd:printf ok exit=0 sha256=000000000000"

        result = replace_evidence(
            tmp_path,
            ticket_id,
            "tests/x.py::test_old",
            fabricated,
            reason="attempted false cmd: replacement",
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed
