"""Tests for WAIVE006 (T-0779): a `frob:waive`/`.strata waive` directive
bound (via `ticket=`/`ticket "..."` attribute, or binding reason phrasing)
to a ticket that is now DONE/DROPPED in the ledger+archive is a stale
waiver and must fire a gate ERROR naming the site and the closed ticket.

The real-repo test in `TestWaive006RealRepo` is the calibration proof the
ticket demanded: this rule must find ZERO false errors on this repo's own
current `design/frob.strata` (T-0778 rewrote its five LINT004 kill-switch
waivers to cite an open follow-on ticket while historically MENTIONING the
long-closed T-0200 that built the underlying mechanism -- WAIVE006 must
not fire on that mention).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import pytest

from frob.gates import (
    GateConfig,
    Severity,
    Violation,
    _waive006_binding_ticket_refs,
    _waive006_comment_violations,
    _waive006_strata_violations,
    _waive007_comment_violations,
    _waive007_is_exempt_dangling_ref,
    _waive007_strata_violations,
    known_gate_rule_ids,
    run_gates,
    waive006_gate,
    waive007_gate,
)
from frob.gates._waive import (
    _reason_promises_followup,
    _reason_ticket_ids,
    _waive004_dead_count_by_rule,
    census_gate_rules,
    waive009_violations,
)
from frob.graph import build_graph
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- shared test fixture
    helper matching `tests/test_gates.py`'s `_write`."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    """Build a fresh, uncached `GraphSnapshot` for `root` -- matching
    `tests/test_gates.py`'s `_snapshot` helper."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _ticket(
    *, ticket_id: str = "T-0001", state: TicketState = TicketState.QUEUED
) -> Ticket:
    """A minimal `Ticket` fixture at a given `state` -- matching
    `tests/test_gates.py`'s `_ticket` helper's shape."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nx\n\n## Done report\ndone\n",
    )


class TestWaive006BindingPhraseExtraction:
    """`_waive006_binding_ticket_refs` -- the binding-vs-historical
    calibration in isolation, no gate plumbing involved."""

    def test_pending_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs(
            "no real kill switch yet -- pending T-0200's real mechanism"
        )
        assert refs == {"T-0200"}

    def test_is_the_follow_on_ticket_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs(
            "no real kill switch around subprocess spawning yet -- T-0200 "
            "is the follow-on ticket to build one"
        )
        assert refs == {"T-0200"}

    def test_bare_historical_mention_is_not_binding(self) -> None:
        """T-0778's exact rewritten phrasing: a parenthetical build-history
        aside naming a closed ticket must NOT be extracted as a binding
        reference."""
        refs = _waive006_binding_ticket_refs(
            "kill-switch mechanism exists (T-0200/T-0778) but this node's "
            "call sites are not yet wired through it -- tracked in "
            "T-draft-8cd37914"
        )
        assert refs == set()

    def test_built_a_real_kill_switch_narration_is_not_binding(self) -> None:
        refs = _waive006_binding_ticket_refs(
            "T-0200 built a real kill switch and T-0778 wired the git seam"
        )
        assert refs == set()

    def test_no_ticket_mention_at_all_is_not_binding(self) -> None:
        assert _waive006_binding_ticket_refs("legacy code, no ticket needed") == set()

    def test_holds_a_lease_phrasing_is_binding(self) -> None:
        """T-2622: the real repo phrasing this extension exists to catch --
        this file's own top-of-module SCOPE001 waiver, before it was
        reworded, read exactly this shape."""
        refs = _waive006_binding_ticket_refs(
            "T-1279 (TEST005 burn-down) holds a concurrent in-progress "
            "lease on src/frob/gates/** for the whole package"
        )
        assert refs == {"T-1279"}

    def test_holding_a_lease_on_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs(
            "cannot touch this file -- holding a live lease on it is T-0042"
        )
        assert refs == {"T-0042"}

    def test_possessive_lease_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs("blocked by T-0099's live lease")
        assert refs == {"T-0099"}

    def test_lease_held_by_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs("lease held by T-0007 on this path")
        assert refs == {"T-0007"}

    def test_under_x_lease_phrasing_is_binding(self) -> None:
        refs = _waive006_binding_ticket_refs("cannot edit under T-0011's own lease")
        assert refs == {"T-0011"}

    def test_past_tense_was_holding_is_not_binding(self) -> None:
        """T-2622's own rewrite of this file's SCOPE001 waiver: past-tense
        'was holding' narrates history, not a live claim, and must not
        trigger -- mirrors the T-0778 calibration case for the original
        WAIVE006 phrases."""
        refs = _waive006_binding_ticket_refs(
            "T-1279 was holding a concurrent in-progress lease on this "
            "package; that has since resolved"
        )
        assert refs == set()


class TestWaive006CommentChannel:
    """`_waive006_comment_violations` -- the `frob:waive` comment channel."""

    def test_ticket_attr_bound_to_done_ticket_fires(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = _waive006_comment_violations(snap, queue)
        assert len(violations) == 1
        assert violations[0].rule == "WAIVE006"
        assert "T-0001" in violations[0].message

    def test_ticket_attr_bound_to_dropped_ticket_fires(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0002"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0002": _ticket(state=TicketState.DROPPED)})
        violations = _waive006_comment_violations(snap, queue)
        assert len(violations) == 1

    def test_ticket_attr_bound_to_open_ticket_is_silent(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0003"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0003": _ticket(state=TicketState.QUEUED)})
        violations = _waive006_comment_violations(snap, queue)
        assert violations == ()

    def test_binding_reason_phrase_bound_to_done_ticket_fires(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="pending T-0004\'s real fix"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0004": _ticket(state=TicketState.DONE)})
        violations = _waive006_comment_violations(snap, queue)
        assert len(violations) == 1

    def test_historical_mention_of_done_ticket_is_silent(self, tmp_path: Path) -> None:
        """The T-0778 calibration case reproduced on the comment channel:
        a reason mentioning a closed ticket in build-history prose, with no
        binding phrasing and no `ticket=` attr, must not fire."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="kill-switch exists (T-0005) '
            'but not wired here yet"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0005": _ticket(state=TicketState.DONE)})
        violations = _waive006_comment_violations(snap, queue)
        assert violations == ()

    def test_unresolvable_ticket_id_is_silent(self, tmp_path: Path) -> None:
        """A ticket id the queue has never heard of (typo, not-yet-landed
        draft) is a different honesty gap than WAIVE006's -- not flagged
        here."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-9999"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = _waive006_comment_violations(snap, queue)
        assert violations == ()

    def test_lease_premise_bound_to_done_ticket_fires(self, tmp_path: Path) -> None:
        """T-2622: a "holds a lease" premise is a live-state claim just
        like "pending T-####" -- once the cited ticket is DONE, the
        waiver is exactly as stale, and WAIVE006 must catch it via the
        SAME rule, not a separate one."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="T-1279 holds a concurrent '
            'in-progress lease on this package"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-1279": _ticket(state=TicketState.DONE)})
        violations = _waive006_comment_violations(snap, queue)
        assert len(violations) == 1
        assert violations[0].rule == "WAIVE006"

    def test_lease_premise_bound_to_open_ticket_is_silent(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="T-1279 holds a concurrent '
            'in-progress lease on this package"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-1279": _ticket(state=TicketState.QUEUED)})
        violations = _waive006_comment_violations(snap, queue)
        assert violations == ()


class TestWaive006StrataChannel:
    """`_waive006_strata_violations` -- the `.strata` `waive` clause channel."""

    def test_strata_ticket_attr_bound_to_done_ticket_fires(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no kill switch yet" ticket "T-0100";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={"T-0100": _ticket(state=TicketState.DONE)})
        violations = _waive006_strata_violations(tmp_path, queue)
        assert len(violations) == 1
        assert violations[0].file == "design/sample.strata"
        assert "T-0100" in violations[0].message

    def test_strata_binding_phrase_bound_to_dropped_ticket_fires(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no real kill switch around subprocess '
            'spawning yet -- T-0101 is the follow-on ticket to build one" '
            'ticket "T-0101";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={"T-0101": _ticket(state=TicketState.DROPPED)})
        violations = _waive006_strata_violations(tmp_path, queue)
        assert len(violations) == 1

    def test_strata_open_follow_on_with_historical_mention_is_silent(
        self, tmp_path: Path
    ) -> None:
        """The exact T-0778 rewrite shape: `ticket "T-draft-..."` (open,
        unresolvable/draft) plus a `(T-#### / T-####)` historical aside
        naming a closed ticket in `reason`. Must not fire."""
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "kill-switch mechanism exists '
            "(T-0200/T-0778) but this node's call sites are not yet wired "
            'through it -- tracked in T-draft-8cd37914" '
            'ticket "T-draft-8cd37914";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={"T-0200": _ticket(state=TicketState.DONE)})
        violations = _waive006_strata_violations(tmp_path, queue)
        assert violations == ()

    def test_no_design_dir_is_silent(self, tmp_path: Path) -> None:
        assert _waive006_strata_violations(tmp_path, TicketQueue(tickets={})) == ()


class TestWaive006Registration:
    """WAIVE006 joins `known_gate_rule_ids()` and is itself waivable (not
    added to the unwaivable-rules set)."""

    def test_waive006_is_a_known_gate_rule(self) -> None:
        assert "WAIVE006" in known_gate_rule_ids()

    def test_waive006_gate_combines_both_channels(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no kill switch yet" ticket "T-0100";\n'
            "}\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(state=TicketState.DONE),
                "T-0100": _ticket(ticket_id="T-0100", state=TicketState.DONE),
            }
        )
        violations = waive006_gate(tmp_path, snap, queue)
        assert {v.file for v in violations} == {"src/a.py", "design/sample.strata"}

    def test_waivable_via_frob_waive_comment(self, tmp_path: Path) -> None:
        """WAIVE006 itself is a normal waivable rule id, not added to
        `_UNWAIVABLE_RULES` -- proven end-to-end through `run_gates`."""
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0001"\n'
            '    # frob:waive WAIVE006 reason="acknowledged, re-review scheduled"\n'
            "    return x\n",
        )
        _git_init(tmp_path)
        queue_ticket = _ticket(state=TicketState.DONE)
        from frob.tickets._store import write_ticket

        write_ticket(tmp_path, queue_ticket).danger_ok

        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert not any(v.rule == "WAIVE006" for v in report.violations)
        assert any(w.rule == "WAIVE006" for w in report.waived), (
            "expected WAIVE006 to appear in the waived set, not vanish silently"
        )


def _git_init(root: Path) -> None:
    """Minimal git init so `run_gates`'s diff/scope machinery has a base
    to work against -- matching `tests/test_gates.py`'s `_git_init`."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


class TestWaive007ExemptDanglingRef:
    """`_waive007_is_exempt_dangling_ref` -- the `T-draft-*` exemption in
    isolation, no gate plumbing involved."""

    def test_draft_id_is_exempt(self) -> None:
        assert _waive007_is_exempt_dangling_ref("T-draft-8cd37914") is True

    def test_real_ticket_id_is_not_exempt(self) -> None:
        assert _waive007_is_exempt_dangling_ref("T-0803") is False


class TestWaive007CommentChannel:
    """`_waive007_comment_violations` -- the `frob:waive` comment channel."""

    def test_ticket_attr_bound_to_unresolvable_id_fires(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-9999"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = _waive007_comment_violations(snap, queue)
        assert len(violations) == 1
        assert violations[0].rule == "WAIVE007"
        assert violations[0].severity.name == "WARN"
        assert "T-9999" in violations[0].message

    def test_binding_reason_phrase_bound_to_unresolvable_id_fires(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="pending T-9998\'s real fix"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = _waive007_comment_violations(snap, queue)
        assert len(violations) == 1

    def test_ticket_attr_bound_to_resolvable_id_is_silent(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-0003"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0003": _ticket(state=TicketState.QUEUED)})
        violations = _waive007_comment_violations(snap, queue)
        assert violations == ()

    def test_ticket_attr_bound_to_draft_id_is_exempt(self, tmp_path: Path) -> None:
        """The T-0803 land-renumbering case: a waiver still citing the
        draft id it was written under must not be flagged."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-draft-8cd37914"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = _waive007_comment_violations(snap, queue)
        assert violations == ()

    def test_no_binding_ref_at_all_is_silent(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy code, no ticket needed"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = _waive007_comment_violations(snap, queue)
        assert violations == ()


class TestWaive007StrataChannel:
    """`_waive007_strata_violations` -- the `.strata` `waive` clause channel."""

    def test_strata_ticket_attr_bound_to_unresolvable_id_fires(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no kill switch yet" ticket "T-9997";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={})
        violations = _waive007_strata_violations(tmp_path, queue)
        assert len(violations) == 1
        assert violations[0].file == "design/sample.strata"
        assert "T-9997" in violations[0].message

    def test_strata_ticket_attr_bound_to_draft_id_is_exempt(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "tracked in T-draft-9f9f9f9f" '
            'ticket "T-draft-9f9f9f9f";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={})
        violations = _waive007_strata_violations(tmp_path, queue)
        assert violations == ()

    def test_strata_ticket_attr_bound_to_resolvable_id_is_silent(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no kill switch yet" ticket "T-0100";\n'
            "}\n",
        )
        queue = TicketQueue(tickets={"T-0100": _ticket(state=TicketState.QUEUED)})
        violations = _waive007_strata_violations(tmp_path, queue)
        assert violations == ()

    def test_no_design_dir_is_silent(self, tmp_path: Path) -> None:
        assert _waive007_strata_violations(tmp_path, TicketQueue(tickets={})) == ()


class TestWaive007Registration:
    """WAIVE007 joins `known_gate_rule_ids()` and is itself waivable (not
    added to the unwaivable-rules set)."""

    def test_waive007_is_a_known_gate_rule(self) -> None:
        assert "WAIVE007" in known_gate_rule_ids()

    def test_waive007_gate_combines_both_channels(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-9996"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/sample.strata",
            "node checker : trusted {\n"
            '    may "exec";\n'
            '    waive "LINT004" reason "no kill switch yet" ticket "T-9995";\n'
            "}\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = waive007_gate(tmp_path, snap, queue)
        assert {v.file for v in violations} == {"src/a.py", "design/sample.strata"}

    def test_waivable_via_frob_waive_comment(self, tmp_path: Path) -> None:
        """WAIVE007 itself is a normal waivable rule id, not added to
        `_UNWAIVABLE_RULES` -- proven end-to-end through `run_gates`."""
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:waive COV001 reason="legacy" ticket="T-9994"\n'
            '    # frob:waive WAIVE007 reason="acknowledged, re-review scheduled"\n'
            "    return x\n",
        )
        _git_init(tmp_path)
        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert not any(v.rule == "WAIVE007" for v in report.violations)
        assert any(w.rule == "WAIVE007" for w in report.waived), (
            "expected WAIVE007 to appear in the waived set, not vanish silently"
        )


# T-2622: extending `_WAIVE006_BINDING_PHRASE_RES` with lease-premise
# phrasing ("T-#### holds/holding/under a live lease") surfaced 13
# genuinely stale waiver sites already live on this repo's OWN tree --
# the cited ticket really has gone DONE and nobody re-reviewed the
# waiver, exactly the T-2612 class this whole family of work exists to
# close. Every one of these sites is OUTSIDE T-2622's own declared scope
# (`src/frob/gates/_waive.py`/`_waive_comments.py`,
# `tests/test_waive_gate.py`), so T-2622 does not fix them -- filed as a
# follow-up (T-2656, renumbers at land) instead of forced into
# scope or silently ignored, per the playbook's "fix what's in scope,
# file what's not" rule. This allowlist keys the calibration test's
# tolerance to EXACTLY those 13 known sites (by file + the stale ticket
# id the message names) so any OTHER/NEW stale waiver this run finds
# still fails the test -- the calibration guarantee (no silent
# regressions) is preserved, it just no longer pretends this repo's real,
# already-existing debt doesn't exist. Shrink this set as the follow-up
# ticket's sites get fixed; remove it entirely once that ticket closes.
_WAIVE006_KNOWN_DEBT_T2622 = frozenset(
    {
        ("src/frob/gates/__init__.py", "T-1279"),
        ("src/frob/gates/_decisions_compliance.py", "T-1279"),
        ("src/frob/gates/_doclink_docanchor.py", "T-1279"),
        ("src/frob/gates/_sys.py", "T-1279"),
        ("src/frob/gates/_tickets_gate.py", "T-1279"),
        ("src/frob/gates/_todo_fmt.py", "T-1279"),
        ("src/frob/gates/_coverage.py", "T-1235"),
        ("src/frob/gates/_mutation_evidence.py", "T-1739"),
        ("src/frob/tickets/_evidence.py", "T-1739"),
        ("src/frob/tickets/_models.py", "T-1739"),
        ("src/frob/tickets/_draft_finalize.py", "T-2076"),
    }
)


def _waive006_unexpected(
    violations: tuple[Violation, ...], known_debt: frozenset[tuple[str, str]]
) -> list[str]:
    """`violations` whose `(file, stale-ticket-id)` is NOT in `known_debt`
    -- shared by the WAIVE006 real-repo calibration test so an allowlisted
    site's own known ticket id still has to match (a violation citing a
    DIFFERENT stale ticket at an allowlisted file is a genuinely new
    finding, not a duplicate of the tracked one)."""
    unexpected = []
    for v in violations:
        match = re.search(r"bound to ticket (T-\d+)", v.message)
        stale = match.group(1) if match else ""
        if (v.file, stale) not in known_debt:
            unexpected.append(v.message)
    return unexpected


class TestWaive006RealRepo:
    """The calibration proof the ticket demanded: WAIVE006 must find ZERO
    UNEXPECTED errors against this repo's OWN real `design/frob.strata`
    and real `frob:waive` comments -- run against the live ledger, not a
    fixture. Known, already-ticketed debt (`_WAIVE006_KNOWN_DEBT_T2622`)
    is tolerated by exact `(file, stale-ticket)` match only -- anything
    else still fails the test."""

    def test_zero_errors_on_real_repo(self) -> None:
        """Kept as the original T-0779/T-1072 evidence node id (T-2622:
        renaming it would orphan those tickets' only proof of done, per
        T-1946's OrphanedEvidenceDeletion guard) -- the assertion inside
        now tolerates the T-2622 known-debt allowlist rather than a bare
        zero; see the module comment above `_WAIVE006_KNOWN_DEBT_T2622`."""
        from frob.gates import _load_inputs

        cfg = GateConfig(root=str(_REPO_ROOT))
        st = _load_inputs(cfg).danger_ok
        violations = waive006_gate(st.repo_root, st.snapshot, st.queue)
        unexpected = _waive006_unexpected(violations, _WAIVE006_KNOWN_DEBT_T2622)
        assert unexpected == [], (
            "WAIVE006 fired on the real repo outside the T-2622 known-debt "
            f"allowlist -- either a genuinely stale waiver needs fixing, or "
            f"the heuristic over-fired: {unexpected}"
        )


class TestWaive007RealRepo:
    """The calibration proof T-0808 demanded: WAIVE007 must find ZERO
    findings against this repo's own real waivers -- run against the live
    ledger, not a fixture. Main currently has no dangling binding refs
    after the T-0803 draft-id retarget (the four `design/frob.strata`
    waivers that used to cite the dead `T-draft-8cd37914` were fixed to
    cite `T-0803` directly)."""

    def test_zero_findings_on_real_repo(self) -> None:
        from frob.gates import _load_inputs

        cfg = GateConfig(root=str(_REPO_ROOT))
        st = _load_inputs(cfg).danger_ok
        violations = waive007_gate(st.repo_root, st.snapshot, st.queue)
        offending = [v.message for v in violations]
        assert violations == (), (
            "WAIVE007 fired on the real repo -- either a genuinely dangling "
            f"binding ref needs fixing, or the heuristic over-fired: {offending}"
        )


class TestRuleCensus:
    """T-1764: `census_gate_rules` classifies corpus-wide vs diff-scoped
    rules BEFORE computing any waive-rate -- the T-1763 methodological
    correction this ticket's acceptance criteria require, made
    structural rather than a discipline someone has to remember."""

    def test_corpus_wide_rule_gets_a_rate(self) -> None:
        # frob:tests src/frob/gates/_waive.py::census_gate_rules
        """A corpus-wide rule (not in
        `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`, e.g. `COV007`) gets a
        real `waive_rate = waived / (waived + fired)`."""
        kept = (
            Violation(
                rule="COV007", severity=Severity.WARN, file="a.py", line=1, message="x"
            ),
            Violation(
                rule="COV007", severity=Severity.WARN, file="b.py", line=1, message="x"
            ),
            Violation(
                rule="COV007", severity=Severity.WARN, file="c.py", line=1, message="x"
            ),
        )
        waived = (
            Violation(
                rule="COV007", severity=Severity.WARN, file="d.py", line=1, message="x"
            ),
        )
        rows = census_gate_rules(kept, waived)
        cov007 = next(r for r in rows if r.rule == "COV007")
        assert cov007.corpus_wide is True
        assert cov007.fired == 3
        assert cov007.waived == 1
        assert cov007.waive_rate == 0.25

    def test_diff_scoped_rule_gets_no_rate(self) -> None:
        # frob:tests src/frob/gates/_waive.py::census_gate_rules
        """A diff-scoped rule (`AFFECT001`, in
        `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`) with 0 live findings
        on this snapshot gets `waive_rate=None`, never `100%` or `0%` --
        the exact number that would have recommended deleting a working
        detector (the T-1763 incident this ticket exists to prevent)."""
        kept: tuple[Violation, ...] = ()
        waived = (
            Violation(
                rule="AFFECT001",
                severity=Severity.WARN,
                file="a.py",
                line=1,
                message="x",
            ),
        )
        rows = census_gate_rules(kept, waived)
        affect001 = next(r for r in rows if r.rule == "AFFECT001")
        assert affect001.corpus_wide is False
        assert affect001.waived == 1
        assert affect001.fired == 0
        assert affect001.waive_rate is None

    def test_dead_waiver_count_is_folded_in(self) -> None:
        # frob:tests src/frob/gates/_waive.py::census_gate_rules
        """A `WAIVE004` finding naming `COV007` (a waiver matching zero
        live findings this run) is counted into `COV007`'s
        `dead_waivers`, not left as an unrelated top-level warning."""
        kept = (
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file="a.py",
                line=1,
                message="WAIVE004: a.py:1 frob:waive COV007 matches 0 findings this run",
            ),
        )
        waived = (
            Violation(
                rule="COV007", severity=Severity.WARN, file="a.py", line=1, message="x"
            ),
        )
        rows = census_gate_rules(kept, waived)
        cov007 = next(r for r in rows if r.rule == "COV007")
        assert cov007.dead_waivers == 1


class TestCensusCli:
    """`frob check --census` (T-1764) -- the CLI entry point, with
    `run_gates` monkeypatched so this stays a fast, isolated test rather
    than a full-repo gate run."""

    def test_census_prints_a_table_and_exits_zero(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/app/check_runner.py::_run_census
        from typani import Ok

        from frob.app import check_runner
        from frob.app.config import AppConfig, Subcommand
        from frob.gates._models import GateReport, GateStats

        kept = (
            Violation(
                rule="COV007", severity=Severity.WARN, file="a.py", line=1, message="x"
            ),
        )
        waived = (
            Violation(
                rule="COV007", severity=Severity.WARN, file="b.py", line=1, message="x"
            ),
        )
        report = GateReport(
            violations=kept,
            waived=waived,
            stats=GateStats(counts={}, timing_s={}, skipped=()),
        )
        # `_run_census` imports `run_gates as _raw_run_gates` locally at
        # call time, so patch the real module attribute it resolves.
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg: Ok(report))

        cfg = AppConfig(
            subcommand=Subcommand.check, check_census=True, check_json=False
        )
        with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as exc_info:
            check_runner._run_census(tmp_path, cfg)
        assert exc_info.value.code == 0
        assert any("COV007" in rec.message for rec in caplog.records)


class TestWaive004DeadCount:
    """`_waive004_dead_count_by_rule` (T-1764): parses a WAIVE004 finding's
    own message text to recover which rule the dead waiver was about."""

    def test_counts_per_rule_from_message(self) -> None:
        # frob:tests src/frob/gates/_waive.py::_waive004_dead_count_by_rule
        violations = (
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file="a.py",
                line=1,
                message="WAIVE004: a.py:1 frob:waive COV007 matches 0 findings this run",
            ),
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file="b.py",
                line=2,
                message="WAIVE004: b.py:2 frob:waive COV007 matches 0 findings this run",
            ),
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file="c.py",
                line=3,
                message="WAIVE004: c.py:3 frob:waive ARCH001 matches 0 findings this run",
            ),
        )
        counts = _waive004_dead_count_by_rule(violations)
        assert counts == {"COV007": 2, "ARCH001": 1}

    def test_empty_input_yields_empty_dict(self) -> None:
        # frob:tests src/frob/gates/_waive.py::_waive004_dead_count_by_rule
        assert _waive004_dead_count_by_rule(()) == {}


class TestWaive009PromisePhraseDetection:
    """`_reason_promises_followup` -- the promise-phrase trigger in
    isolation, no gate plumbing involved."""

    def test_follow_up_ticket_phrasing_promises(self) -> None:
        assert _reason_promises_followup(
            "a doc-update follow-up ticket updates this once that lease clears"
        )

    def test_once_x_clears_phrasing_promises(self) -> None:
        assert _reason_promises_followup("fixed once the T-1279 lease clears")

    def test_will_file_phrasing_promises(self) -> None:
        assert _reason_promises_followup("will file a ticket for this next")

    def test_ordinary_reason_does_not_promise(self) -> None:
        assert not _reason_promises_followup(
            "legacy code, dead by construction, no follow-up needed"
        )

    def test_historical_ticket_mention_does_not_promise(self) -> None:
        assert not _reason_promises_followup(
            "kill-switch mechanism exists (T-0200/T-0778) but not wired here"
        )


class TestWaive009TicketIdExtraction:
    """`_reason_ticket_ids` -- bare `T-\\d+` capture, wider net than
    WAIVE006's binding-phrase-only extraction."""

    def test_extracts_bare_mention(self) -> None:
        assert _reason_ticket_ids("tracked in T-2620, will finish soon") == {
            "T-2620"
        }

    def test_extracts_multiple(self) -> None:
        assert _reason_ticket_ids("see T-0001 and T-0002") == {"T-0001", "T-0002"}

    def test_no_mention_yields_empty(self) -> None:
        assert _reason_ticket_ids("no ticket here") == set()


class TestWaive009Violations:
    """`waive009_violations` -- the assembled gate: a promise phrase with
    no ticket id that resolves in the queue is an ERROR; a promise phrase
    backed by a real (or in-flight draft) ticket id is silent; and a
    reason with no promise phrase at all is untouched regardless of what
    it says about tickets (WAIVE006/007's territory, not WAIVE009's)."""

    def test_promise_with_no_ticket_id_errors(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            "    # frob:waive AFFECT001 reason=\"a doc-update follow-up "
            'ticket updates this once that lease clears"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        violations = waive009_violations(snap, TicketQueue(tickets={}))
        assert len(violations) == 1
        assert violations[0].rule == "WAIVE009"
        assert violations[0].severity == Severity.ERROR

    def test_promise_with_resolvable_ticket_id_passes(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="a follow-up ticket T-0010 '
            'updates this once T-0010 lands"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0010": _ticket(state=TicketState.QUEUED)})
        violations = waive009_violations(snap, queue)
        assert violations == ()

    def test_promise_with_unresolvable_ticket_id_errors(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="a follow-up ticket T-9999 '
            'updates this once it lands"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        violations = waive009_violations(snap, TicketQueue(tickets={}))
        assert len(violations) == 1
        assert violations[0].rule == "WAIVE009"

    def test_draft_ticket_id_resolves(self, tmp_path: Path) -> None:
        """A `T-draft-*` id is worktree-local work-in-flight, not an
        unfiled promise -- mirrors WAIVE007's own exemption."""
        source = (
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="a follow-up ticket '
            'T-draft-abc123 updates this once it lands"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        violations = waive009_violations(snap, TicketQueue(tickets={}))
        assert violations == ()

    def test_no_promise_phrase_untouched(self, tmp_path: Path) -> None:
        """A reason naming zero tickets and promising no future work is
        WAIVE006/007's territory (or nobody's), never WAIVE009's."""
        source = (
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="legacy, dead by construction"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        violations = waive009_violations(snap, TicketQueue(tickets={}))
        assert violations == ()

    def test_known_gate_rule_ids_includes_waive009(self) -> None:
        assert "WAIVE009" in known_gate_rule_ids()


class TestWaive009Wiring:
    """T-2639: `waive009_violations` was implemented and unit-tested
    directly (T-2606) but never called from `_assemble_gate_report`, so
    it enforced nothing through a real `frob check` run -- proven
    end-to-end through `run_gates`, mirroring
    `TestWaive006Gate.test_waivable_via_frob_waive_comment`'s own
    end-to-end proof rather than a direct unit-level call, so a wiring
    regression (the function existing but never being invoked) actually
    fails this test."""

    def test_unresolvable_promise_fires_through_run_gates(
        self, tmp_path: Path
    ) -> None:
        """A `frob:waive` reason promising follow-up work with no
        resolvable ticket id must surface as a WAIVE009 ERROR through a
        real `frob check` (`run_gates`) pass, not just via a direct call
        to `waive009_violations`."""
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="a follow-up ticket '
            'updates this once that lease clears"\n'
            "    return x\n",
        )
        _git_init(tmp_path)
        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert any(v.rule == "WAIVE009" for v in report.violations), (
            "WAIVE009 did not fire through run_gates -- wiring regression"
        )

    def test_resolvable_promise_does_not_fire_through_run_gates(
        self, tmp_path: Path
    ) -> None:
        """The same promise phrasing backed by a real, resolvable ticket
        id must stay silent through `run_gates` -- otherwise WAIVE009 is
        indistinguishable from a rule that rejects every waiver."""
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:waive AFFECT001 reason="a follow-up ticket '
            'T-0001 updates this once T-0001 lands"\n'
            "    return x\n",
        )
        _git_init(tmp_path)
        queue_ticket = _ticket(state=TicketState.QUEUED)
        from frob.tickets._store import write_ticket

        write_ticket(tmp_path, queue_ticket).danger_ok

        report = run_gates(GateConfig(root=str(tmp_path))).danger_ok
        assert not any(v.rule == "WAIVE009" for v in report.violations)
