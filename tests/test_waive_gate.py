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

from datetime import date
from pathlib import Path

from frob.gates import (
    GateConfig,
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


class TestWaive006RealRepo:
    """The calibration proof the ticket demanded: WAIVE006 must find ZERO
    false errors against this repo's OWN real `design/frob.strata` and
    real `frob:waive` comments -- run against the live ledger, not a
    fixture."""

    def test_zero_errors_on_real_repo(self) -> None:
        from frob.gates import _load_inputs

        cfg = GateConfig(root=str(_REPO_ROOT))
        st = _load_inputs(cfg).danger_ok
        violations = waive006_gate(st.repo_root, st.snapshot, st.queue)
        offending = [v.message for v in violations]
        assert violations == (), (
            "WAIVE006 fired on the real repo -- either a genuinely stale "
            f"waiver needs fixing, or the heuristic over-fired: {offending}"
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
