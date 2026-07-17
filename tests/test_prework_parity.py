"""Regression: the pre-work sweep digest recorded by `frob ticket start/sweep`
and the digest `prework_gate` compares against MUST be the same function.

Two independent implementations shipped once (path:digest vs path:digest\\n,
hand-rolled glob vs fnmatch) and PRE001 could then only pass when a ticket's
scope matched zero files -- observed as "flaky PRE001" during the docs
dogfood. This file pins the single-source-of-truth contract.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from typani.option import Some

from frob.gates import PreworkSweep, prework_gate, scope_digest
from frob.graph import build_graph
from frob.tickets import Origin as TicketOrigin
from frob.tickets import Ticket, TicketKind, TicketState


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
    (pkg / "other.py").write_text("def gn():\n    return 2\n", encoding="utf-8")
    return root


def _ticket(scope: tuple[str, ...]) -> Ticket:
    return Ticket(
        id="T-9001",
        title="parity",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.FEATURE,
        origin=TicketOrigin.HUMAN,
        created=date.today(),
        blocked_by=(),
        parent=None,
        scope=scope,
        evidence=(),
        attachments=(),
        body="",
    )


class TestScopeDigestParity:
    def test_recorded_digest_satisfies_gate(self, tmp_path):
        root = _make_repo(tmp_path)
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok
        ticket = _ticket(("src/pkg/**",))

        sweep = PreworkSweep(
            date=date.today(),
            dup_findings=0,
            xref_hits=(),
            digest=scope_digest(ticket.scope, snapshot),
        )
        violations = prework_gate(ticket, snapshot, Some(sweep))
        assert violations == ()

    def test_gate_fires_when_scope_files_change(self, tmp_path):
        root = _make_repo(tmp_path)
        cache = root / ".frob" / "cache.db"
        snapshot = build_graph(root, cache).danger_ok
        ticket = _ticket(("src/pkg/**",))
        sweep = PreworkSweep(
            date=date.today(),
            dup_findings=0,
            xref_hits=(),
            digest=scope_digest(ticket.scope, snapshot),
        )

        (root / "src" / "pkg" / "mod.py").write_text(
            "def fn():\n    return 99\n", encoding="utf-8"
        )
        rebuilt = build_graph(root, cache).danger_ok
        violations = prework_gate(ticket, rebuilt, Some(sweep))
        assert any(v.rule == "PRE001" for v in violations)

    def test_empty_scope_matches_no_files_not_everything(self, tmp_path):
        root = _make_repo(tmp_path)
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert scope_digest((), snapshot) == scope_digest(("no/such/dir/**",), snapshot)


class TestCliStartRecordsGateCompatibleDigest:
    def test_start_then_gate_is_clean(self, tmp_path):
        """End-to-end: `frob ticket new` + `start` (queued auto-plan path)
        records a sweep the prework gate accepts against a fresh snapshot."""
        root = _make_repo(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        frob = [sys.executable, "-m", "frob"]

        new = subprocess.run(
            [
                *frob,
                "ticket",
                "new",
                "--title",
                "parity e2e",
                "--kind",
                "feature",
                "--scope",
                "src/pkg/**",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert new.returncode == 0, new.stderr
        ticket_id = next(
            part for part in new.stdout.split() if part.startswith("T-")
        ).strip(":")

        start = subprocess.run(
            [*frob, "ticket", "start", ticket_id],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert start.returncode == 0, start.stderr

        check = subprocess.run(
            [*frob, "check", "--only", "prework", "--ticket", ticket_id],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert "PRE001" not in check.stdout + check.stderr, (
            check.stdout + check.stderr
        )
