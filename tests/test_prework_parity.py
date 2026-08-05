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

    # frob:ticket T-0355
    def test_digest_is_content_only_portable_across_checkouts(self, tmp_path):
        """T-0355 (item 3): `scope_digest` keys on (repo-relative path,
        sha256-of-content) -- `_content_hash` never folds in mtime/size, so
        two independent checkouts with byte-identical scope files under the
        same relative layout MUST record the same digest, even though they
        live at different absolute roots. This pins that contract so a
        future change that keys on `_stat_key` (mtime, size) instead of the
        content hash -- which would make a recorded sweep checkout-
        specific -- shows up as a failing test, not a silent regression."""
        root_a = _make_repo(tmp_path / "checkout-a")
        root_b = _make_repo(tmp_path / "checkout-b")
        snapshot_a = build_graph(root_a, root_a / ".frob" / "cache.db").danger_ok
        snapshot_b = build_graph(root_b, root_b / ".frob" / "cache.db").danger_ok
        assert root_a != root_b
        assert scope_digest(("src/pkg/**",), snapshot_a) == scope_digest(
            ("src/pkg/**",), snapshot_b
        )


class TestCliStartRecordsGateCompatibleDigest:
    def test_start_then_gate_is_clean(self, tmp_path):
        """End-to-end: `frob ticket new` + `start` (queued auto-plan path)
        records a sweep the prework gate accepts against a fresh snapshot."""
        root = _make_repo(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        # T-1321: a bare CI runner has no user.name/user.email in its git
        # config, and `frob ticket new`'s auto-commit of tickets.md
        # (_add_and_commit_tickets_md) runs a plain `git commit` that then
        # fails rc=128 with "Author identity unknown" -- set a throwaway
        # local identity so this fixture repo is hermetic regardless of the
        # runner's own global git config.
        # frob:waive PII012 reason="'user.name'/'user.email' here are git's own config keys, not a real person's identity -- this fixture sets a throwaway local git identity so the ledger commit succeeds hermetically"  # noqa: E501
        subprocess.run(
            ["git", "config", "user.name", "frob-test"], cwd=root, check=True
        )
        # frob:waive PII011 reason="'frob-test@example.invalid' is a synthetic throwaway identity for a hermetic git commit in a tmp_path fixture repo, not a real person's email; .invalid is the RFC 2606 reserved non-routable TLD"  # noqa: E501
        subprocess.run(
            ["git", "config", "user.email", "frob-test@example.invalid"],
            cwd=root,
            check=True,
        )
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

        # T-0474: `start` backgrounds the sweep by default now -- this test
        # wants the synchronous, immediately-consistent old contract, which
        # `--foreground` still provides.
        start = subprocess.run(
            [*frob, "ticket", "start", ticket_id, "--foreground"],
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
        assert "PRE001" not in check.stdout + check.stderr, check.stdout + check.stderr
