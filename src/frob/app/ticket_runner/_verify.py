"""frob.app.ticket_runner._verify -- the `evidence`/`done-report` command
family plus the shared check-spawn/evidence-verification helpers.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.process._guard import ProcessGuardError

_log = get_logger("frob.app.ticket_runner")


def _evidence(root: Path, cfg: AppConfig) -> None:
    """Validate `cfg.ticket_evidence_ids` against collected pytest node ids
    and append the resolvable ones to the ticket's structured evidence list;
    or, with `--evidence-cmd`, record the T-0215 non-pytest cmd-evidence
    entry instead (docs-kind tickets only); or, with `--replace OLD NEW`
    (T-1537), rebind an existing evidence id everywhere it appears; or,
    with `--designate-repro NODE-ID` (T-1670), mark one bound evidence id
    as BUG002's explicit repro test (T-1929: validated against the parent
    commit at designate time -- see `_evidence_apply_designate_repro`); or,
    with `--check-repro [NODE-ID]` (T-1929), run that SAME parent-commit
    classification on demand WITHOUT mutating anything and exit -- this
    channel is read-only and handled first, before the "requires at least
    one of" dispatch below, since it never reaches the mutating channels
    or the ledger commit at the bottom of this function. Requires at least
    one of the mutating four -- none of them is silently a no-op. Each
    channel's own apply-and-exit-on-error step is a small helper
    (`_evidence_apply_*`, ARCH001 split) so this dispatcher stays a thin
    sequence of "if given, apply" checks."""
    if cfg.ticket_check_repro is not None:
        if cfg.ticket_id is None:
            _log.error("frob ticket evidence --check-repro requires <id>")
            sys.exit(1)
        _evidence_check_repro(root, cfg)
        return

    has_evidence = (
        cfg.ticket_evidence_ids
        or cfg.ticket_evidence_cmd
        or cfg.ticket_evidence_replace
        or cfg.ticket_designate_repro
    )
    if cfg.ticket_id is None or not has_evidence:
        _log.error(
            "frob ticket evidence requires <id> and one of "
            "<pytest-node-id>..., --evidence-cmd 'command', "
            "--replace OLD-NODE-ID NEW-NODE-ID, --designate-repro NODE-ID, "
            "or --check-repro [NODE-ID]"
        )
        sys.exit(1)

    _evidence_apply_node_ids(root, cfg)
    _evidence_apply_cmd(root, cfg)
    _evidence_apply_replace(root, cfg)
    _evidence_apply_designate_repro(root, cfg)

    # frob:ticket T-1178
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): record evidence for {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


def _evidence_apply_node_ids(root: Path, cfg: AppConfig) -> None:
    """`_evidence`'s positional-node-id channel (ARCH001 split): a no-op
    when `cfg.ticket_evidence_ids` is empty, else applies and exits 1 on
    failure -- same shape every `_evidence_apply_*` helper follows."""
    if not cfg.ticket_evidence_ids:
        return
    assert cfg.ticket_id is not None
    result = _apply_evidence(
        root, cfg.ticket_id, cfg.ticket_evidence_ids, cfg.ticket_accepts
    )
    if result.is_err:
        sys.exit(1)


def _evidence_apply_cmd(root: Path, cfg: AppConfig) -> None:
    """`_evidence`'s `--evidence-cmd` channel (ARCH001 split)."""
    if not cfg.ticket_evidence_cmd:
        return
    assert cfg.ticket_id is not None
    cmd_result = _apply_cmd_evidence(
        root, cfg.ticket_id, cfg.ticket_evidence_cmd, cfg.ticket_accepts
    )
    if cmd_result.is_err:
        sys.exit(1)


# frob:ticket T-1733
def _evidence_apply_replace(root: Path, cfg: AppConfig) -> None:
    """`_evidence`'s `--replace OLD NEW (--reason TEXT | --reason-file
    PATH)` channel (ARCH001 split, T-1537; `--reason` required as of
    T-1733 -- the same "no reason, no mutation" refusal `frob ticket
    scope` already enforces, applied here so weakening what proves a
    ticket costs at least as much bookkeeping as the honest
    `--skip-mutation-evidence` escape hatch)."""
    if not cfg.ticket_evidence_replace:
        return
    assert cfg.ticket_id is not None
    reason = _resolve_evidence_replace_reason(cfg)
    if not reason:
        _log.error(
            "ticket evidence --replace requires --reason TEXT or "
            "--reason-file PATH (T-1733)"
        )
        sys.exit(1)
    replace_result = _apply_replace_evidence(
        root,
        cfg.ticket_id,
        cfg.ticket_evidence_replace,
        reason=reason,
        archived=cfg.ticket_evidence_archived,
    )
    if replace_result.is_err:
        sys.exit(1)


# frob:ticket T-1670
# frob:ticket T-1851
def _evidence_apply_designate_repro(root: Path, cfg: AppConfig) -> None:
    """`_evidence`'s `--designate-repro NODE-ID` channel (ARCH001 split,
    T-1670): marks `cfg.ticket_designate_repro` as the ticket's explicit
    BUG002 repro test via `set_designated_repro_test` -- see that
    function's own docstring for the "must already be bound as evidence"
    requirement.

    T-1851: threads `--designate-repro-reason`/`--designate-repro-reason-
    file` through to `set_designated_repro_test`'s `reason` kwarg (T-1749's
    audit trail, previously always `None` in practice since nothing wired
    the CLI to it), and REQUIRES a reason when this call is a genuine
    REdesignation (an already-set `designated_repro_test` changing to a
    DIFFERENT bound id) -- the same `EvidenceReplaceReasonMissing`-shaped
    refusal T-1733 already enforces for `--replace`. A first-time
    designation, or a redundant re-designation of the same id, needs no
    reason (nothing was actually redirected -- see `_redesignation_entry`'s
    own docstring in `frob.tickets._setters`)."""
    if not cfg.ticket_designate_repro:
        return
    assert cfg.ticket_id is not None
    from frob.tickets import set_designated_repro_test

    _validate_designate_repro_at_parent(root, cfg)

    reason = _resolve_designate_repro_reason(cfg)
    is_redesignation = _is_genuine_redesignation(
        root, cfg.ticket_id, cfg.ticket_designate_repro
    )
    if is_redesignation and not reason:
        _log.error(
            "ticket evidence --designate-repro: redesignating an already-"
            "set repro test to a different id requires --designate-repro-"
            "reason TEXT or --designate-repro-reason-file PATH (T-1851, "
            "mirroring T-1733's --replace --reason precedent)"
        )
        sys.exit(1)
    designate_result = set_designated_repro_test(
        root, cfg.ticket_id, cfg.ticket_designate_repro, reason=reason
    )
    if designate_result.is_err:
        sys.exit(1)


# frob:ticket T-1929
def _bug_repro_outcome_message(outcome, node_id: str, parent_ref: str) -> str:  # noqa: ANN001
    """Human-readable, outcome-specific message for one `BugReproOutcome`
    (T-1929's three(+)-way classification) -- shared by
    `_validate_designate_repro_at_parent` (requirement A) and
    `_evidence_check_repro` (requirement B) so the wording an agent sees
    at designate time and on demand is identical, not two independently
    drifting copies of the same explanation. `outcome` is typed loosely
    (no import-time dependency on `frob.gates.BugReproOutcome`'s enum
    identity here) but is always one of that enum's six members in
    practice (T-2025 added `TEST_ABSENT_AT_PARENT`) -- every call site
    passes a value straight from `bug_repro_outcome_at_ref`."""
    from frob.gates import BugReproOutcome

    name = outcome.name
    if outcome is BugReproOutcome.FAILED_AT_PARENT:
        return (
            f"FAILED_AT_PARENT: {node_id!r} genuinely fails at {parent_ref} -- "
            f"a real repro, this is what BUG002 wants"
        )
    if outcome is BugReproOutcome.PASSED_AT_PARENT:
        return (
            f"PASSED_AT_PARENT: {node_id!r} already PASSES at {parent_ref} -- "
            f"this is confirmatory-only evidence (proves nothing about the "
            f"defect), the exact shape BUG002 refuses at land/close"
        )
    if outcome is BugReproOutcome.NO_VERDICT:
        return (
            f"NO_VERDICT: {node_id!r} could not even COLLECT at {parent_ref} "
            f"(e.g. it calls a function that does not exist there yet) -- "
            f"this is NOT a pass, it is an unresolved verdict; T-1907's "
            f"original incident was exactly this shape"
        )
    if outcome is BugReproOutcome.SAME_AS_HEAD:
        return (
            f"SAME_AS_HEAD: {parent_ref} resolves to HEAD itself, so no "
            f"pre-fix comparison is possible (a direct-commit-to-{parent_ref} "
            f"shape) -- not a pass, an unresolved verdict"
        )
    # frob:ticket T-2025
    if outcome is BugReproOutcome.TEST_ABSENT_AT_PARENT:
        return (
            f"TEST_ABSENT_AT_PARENT: {node_id!r} does not exist AT ALL in "
            f"{parent_ref}'s tree (pytest collected cleanly, zero items "
            f"matched) -- not a pass, not a transient/retryable failure "
            f"either. If {parent_ref} is (or descends from) an already-"
            f"landed ticket's own history, this is PERMANENT and BY "
            f"CONSTRUCTION: `frob ticket land` squashes a ticket's repro "
            f"test and its fix into one atomic commit, so no ref in main's "
            f"history ever contains the test without the fix already "
            f"applied -- retroactive post-land verification against main "
            f"alone is not achievable for a newly-added test, no matter "
            f"which commit is chosen. See "
            f"docs/modules/tickets.md#check-repro-post-land-limitation-t-2025. "
            f"If this check is running BEFORE land (inside the ticket's own "
            f"worktree, evidence not yet a squash commit), a real verdict is "
            f"still reachable -- commit the repro test ALONE first, confirm "
            f"it fails against the still-unfixed code, then pass that "
            f"commit's own sha as --base-ref (T-2021's own evidence used "
            f"exactly this technique)."
        )
    return f"{name}: unrecognized outcome for {node_id!r} at {parent_ref}"


# frob:ticket T-1929
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_refuses_passed_at_parent  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_refuses_no_verdict  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_accepts_failed_at_parent  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_force_overrides_loudly  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_non_bug_kind_skips_the_check  # noqa: E501
def _validate_designate_repro_at_parent(root: Path, cfg: AppConfig) -> None:
    """T-1929 requirement A: `--designate-repro NODE-ID` refuses (exit 1,
    no write) unless NODE-ID genuinely `FAILED_AT_PARENT` -- the mistake
    four incidents (T-1907/T-1884/T-1882/T-1911) each made was committed
    at exactly this moment (nothing previously checked whether the
    designated id actually failed at the ticket's parent commit), and
    each one only discovered it when `frob ticket land` refused, far from
    where the mistake happened. This closes that gap at the source.

    Scoped to `bug`/`security`-kind tickets only, mirroring
    `bug_repro_violations`'s own `_ERROR_KINDS` restriction exactly (BUG002
    never fires for any other kind, so validating a designation nothing
    will ever gate on would only be noise); any other kind's designation
    is accepted unchecked, same as before this ticket.

    `--designate-repro-force` is the loud, recorded override (mirroring
    `--skip-mutation-evidence`'s posture): the check still runs and its
    verdict is still logged at WARNING, the override only stops it from
    refusing the write. A merge-base that cannot be resolved degrades to
    a skipped check (logged at WARNING) rather than a refusal -- this
    validation is additive to BUG002's own land/close-time gate, which
    still applies regardless (T-0755's "additive, not sole gate" posture,
    same as `_close_mutation_evidence_for_ticket`)."""
    from frob.gates import BugReproOutcome, bug_repro_outcome_at_ref
    from frob.gitio import _merge_base
    from frob.tickets import TicketKind, load_queue

    assert cfg.ticket_id is not None
    assert cfg.ticket_designate_repro is not None
    node_id = cfg.ticket_designate_repro

    loaded = load_queue(root)
    if loaded.is_err:
        _log.warning(
            "ticket evidence --designate-repro: %s could not load the "
            "ticket queue (%s), skipping the T-1929 parent-commit check",
            cfg.ticket_id,
            loaded.danger_err,
        )
        return
    ticket = loaded.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None or ticket.kind not in (TicketKind.BUG, TicketKind.SECURITY):
        return

    resolved = _merge_base(root, cfg.ticket_base_ref)
    if resolved.is_err:
        _log.warning(
            "ticket evidence --designate-repro: %s could not resolve "
            "merge-base against %s (%s), skipping the T-1929 parent-"
            "commit check",
            cfg.ticket_id,
            cfg.ticket_base_ref,
            resolved.danger_err,
        )
        return
    parent_ref = resolved.danger_ok

    outcome = bug_repro_outcome_at_ref(root, node_id, parent_ref)
    message = _bug_repro_outcome_message(outcome, node_id, parent_ref)
    if outcome is BugReproOutcome.FAILED_AT_PARENT:
        _log.info("ticket evidence --designate-repro: %s %s", cfg.ticket_id, message)
        return

    if cfg.ticket_designate_repro_force:
        _log.warning(
            "ticket evidence --designate-repro: %s %s -- FORCED through "
            "via --designate-repro-force, designation recorded anyway "
            "(T-1929 override, use only for a genuine false positive)",
            cfg.ticket_id,
            message,
        )
        return

    _log.error(
        "ticket evidence --designate-repro REFUSED for %s: %s -- this "
        "would be confirmatory-only-or-unresolved evidence, exactly what "
        "BUG002 refuses at land/close (T-1929 moves that check here, at "
        "designate time). Bind a test that actually fails at %s, or pass "
        "--designate-repro-force for a genuine false positive (loud, "
        "recorded override)",
        cfg.ticket_id,
        message,
        parent_ref,
    )
    sys.exit(1)


# frob:ticket T-1929
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_failed_at_parent_exit0  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_passed_at_parent_exit1  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_no_node_id_resolves_designated_test  # noqa: E501
def _evidence_check_repro(root: Path, cfg: AppConfig) -> None:
    """`frob ticket evidence <id> --check-repro [NODE-ID]` (T-1929
    requirement B): the on-demand, read-only twin of
    `_validate_designate_repro_at_parent` -- runs the identical parent-
    commit classification through the SAME shared entrypoint
    (`frob.gates.bug_repro_outcome_at_ref`) and reports the verdict,
    mutating nothing. This exists so an agent mid-ticket can ask "is my
    evidence confirmatory-only?" BEFORE ever calling --designate-repro or
    reaching close/land -- T-1929's `frob ticket reverify` investigation
    found that verb only re-runs BUG002 on an already-DONE ticket, so it
    cannot answer this question while a ticket is still in-progress; this
    fills that specific gap through the same shared gate machinery
    `reverify`/`close`/`land` already use, never a second implementation
    of the repro check itself."""
    assert cfg.ticket_id is not None
    from frob.gates import (
        BugReproOutcome,
        bug_repro_outcome_at_ref,
        designated_repro_test,
    )
    from frob.gitio import _merge_base
    from frob.tickets import load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        _log.error(
            "ticket evidence --check-repro: could not load the ticket queue (%s)",
            loaded.danger_err,
        )
        sys.exit(1)
    ticket = loaded.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("ticket evidence --check-repro: no ticket %s", cfg.ticket_id)
        sys.exit(1)

    node_id = cfg.ticket_check_repro or None
    if not node_id:
        node_id = designated_repro_test(ticket)
    if node_id is None:
        _log.error(
            "ticket evidence --check-repro: %s has no pytest-node-id "
            "evidence bound yet and no NODE-ID was given -- bind evidence "
            "first (`frob ticket evidence %s <node-id>`) or pass a NODE-ID "
            "explicitly",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    resolved = _merge_base(root, cfg.ticket_base_ref)
    if resolved.is_err:
        _log.error(
            "ticket evidence --check-repro: could not resolve merge-base "
            "against %s (%s)",
            cfg.ticket_base_ref,
            resolved.danger_err,
        )
        sys.exit(1)
    parent_ref = resolved.danger_ok

    outcome = bug_repro_outcome_at_ref(root, node_id, parent_ref)
    message = _bug_repro_outcome_message(outcome, node_id, parent_ref)
    if outcome is BugReproOutcome.FAILED_AT_PARENT:
        _log.info("ticket evidence --check-repro: %s %s", cfg.ticket_id, message)
        return
    _log.error("ticket evidence --check-repro: %s %s", cfg.ticket_id, message)
    sys.exit(1)


# frob:ticket T-1851
def _is_genuine_redesignation(root: Path, ticket_id: str, node_id: str) -> bool:
    """Whether designating `node_id` on `ticket_id` would be a genuine
    REdesignation (an already-set `designated_repro_test` changing to a
    DIFFERENT id) -- the same predicate `frob.tickets._setters.
    _redesignation_entry` applies at write time, checked here BEFORE the
    mutation so the CLI can require a reason up front rather than
    discovering the omission after `set_designated_repro_test` already
    wrote an entry with `reason=None`. A ticket that fails to load (never
    happens in practice here -- `_evidence`'s own dispatcher already
    resolved `cfg.ticket_id` against a real ticket by this point) is
    treated as NOT a redesignation, matching `_redesignation_entry`'s own
    `old_value is None` case -- never a false "reason required" refusal
    on an unreadable ticket."""
    from frob.tickets import load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        return False
    ticket = loaded.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        return False
    old_value = ticket.designated_repro_test
    return old_value is not None and old_value != node_id


# frob:ticket T-1851
def _resolve_designate_repro_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket evidence --designate-repro`'s reason (T-1851):
    `--designate-repro-reason-file` wins if given (read verbatim -- T-0737,
    same rationale as `_resolve_evidence_replace_reason`), else the inline
    `--designate-repro-reason` string. Exits 1 if both are given; returns
    `None` if neither is given (the caller only errors on that when the
    designation turns out to be a genuine redesignation)."""
    if (
        cfg.ticket_designate_repro_reason_file is not None
        and cfg.ticket_designate_repro_reason
    ):
        _log.error(
            "ticket evidence --designate-repro: --designate-repro-reason "
            "and --designate-repro-reason-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_designate_repro_reason_file is not None:
        try:
            return cfg.ticket_designate_repro_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket evidence --designate-repro: could not read "
                "--designate-repro-reason-file %s: %s",
                cfg.ticket_designate_repro_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_designate_repro_reason


# frob:ticket T-0458
def _resolve_done_report_why(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket done-report`'s narrative why text: `--why-file`
    wins if given, else `--why` (a literal `-` or an omitted value both
    mean "read stdin", so `frob ticket done-report T-#### -` and a bare
    `frob ticket done-report T-####` piped a narrative both work). Exits 1
    on an unreadable `--why-file`; returns `None` only if reading stdin
    yields nothing meaningful for the caller to act on (never silently
    writes an empty report)."""
    if cfg.ticket_why_file is not None:
        try:
            return cfg.ticket_why_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "done-report: could not read --why-file %s: %s",
                cfg.ticket_why_file,
                exc,
            )
            sys.exit(1)
    if cfg.ticket_why is not None and cfg.ticket_why != "-":
        return cfg.ticket_why
    text = sys.stdin.read()
    return text or None


# frob:ticket T-0754
# frob:ticket T-0754
# The `gate-summary` tool line's leading counts, e.g. "0 errors, 3
# warnings, 12 waived" -- deliberately does NOT match the trailing
# `[archgate=7.99s, ...]` per-gate timing blob `_gate_summary_result`
# appends after it, since that blob is wall-clock and therefore different
# on every single invocation even against an IDENTICAL tree (T-0754 review
# round 2's FATAL fix: a strict-equality re-verification against the RAW
# summary LINE, timing blob included, refused every land, including this
# ticket's own).
_GATE_SUMMARY_COUNTS_RE = re.compile(
    r"gate-summary\s+(\d+)\s+errors?,\s+(\d+)\s+warnings?,\s+(\d+)\s+waived"
)

# frob:ticket T-1703
# The counts-only half of `_GATE_SUMMARY_COUNTS_RE`, without the leading
# `"gate-summary"` anchor: that anchor matched the RENDERED text line's
# own tool-name column (`f"  {icon}  {r.tool:<22}  {r.summary}"`,
# `frob.check._python._gate_summary_result`'s caller), which never
# appears inside `ToolResult.summary` itself -- the JSON payload's
# `results[].summary` field is bare `"N errors, M warnings, K waived
# [timing]"` with no tool-name prefix, since the caller already located
# the right entry by `tool == "gate-summary"` before ever reading this
# field. Used only against a `summary` string already known to belong to
# the `"gate-summary"` `ToolResult` -- unlike `_GATE_SUMMARY_COUNTS_RE`,
# this pattern alone cannot tell a gate-summary line from some other
# tool's summary that happens to share the same shape.
_GATE_SUMMARY_COUNTS_ONLY_RE = re.compile(
    r"^\s*(\d+)\s+errors?,\s+(\d+)\s+warnings?,\s+(\d+)\s+waived"
)


# frob:ticket T-0846
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree \
# kind="unit"
def _python_for_tree(root: Path) -> str:
    """The interpreter that runs `root`'s OWN installed code (T-0846): the
    checked-out tree's `.venv/bin/python` when it exists there, else
    `sys.executable` (the CALLING process's own interpreter) as a
    fallback.

    T-0846: `_check_gates_summary_fn`/`_check_gate_findings_fn` used to
    spawn `sys.executable -m frob check` unconditionally -- whatever
    interpreter the CALLING process happened to run under, not the tree
    being checked. `done-report` capture runs from inside the worktree (its
    own venv, an editable install of the worktree's OWN code); `land`
    re-verification runs from the ROOT checkout (root's venv, `main`'s
    code) but against `root`'s post-merge tree. For a ticket that adds or
    removes a public surface a gate validates against the LIVE, running
    registry (T-0441: a ticket adding a `frob fmt` subcommand), the
    root-venv fresh check's `frob` package has no `fmt` in its own live
    `_build_parser` at all, so a gate that cross-checks a doc/registry
    surface against that live registry (T-0441's concrete reproduction:
    DOC005, README rows naming `frob fmt` as a subcommand "that no longer
    exists" -- 34 rows recorded at capture time vs 33 seen fresh) fires
    deterministically post-merge even though the capture legitimately saw
    zero. `refresh-done-report-and-retry` can never converge for this
    class -- the two runs are checking two DIFFERENT installed trees'
    code, not two views of the same one. Resolving the interpreter from
    `root` itself closes this: both capture and re-verification always run
    the CHECKED tree's own installed code, matching what `uv run frob
    check` would do if invoked there directly.

    Falls back to `sys.executable` (never a hard error) when `root` has no
    `.venv/bin/python` -- a bare checkout with no venv of its own yet, or a
    non-uv-managed tree -- so this is strictly a refinement of the prior
    unconditional `sys.executable`, never a new failure mode."""
    venv_python = root / ".venv" / "bin" / "python"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


# frob:ticket T-0919
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn \
# kind="unit"
def _shared_check_spawn_fn(root: Path, ticket_id: str):  # noqa: ANN201
    """T-0919: build a zero-arg closure that spawns `frob check --ticket
    <id>` in `root` AT MOST ONCE, caching the resulting
    `subprocess.CompletedProcess`-shaped object (or `None` on a refused/
    unmeasurable spawn) so every later call returns the SAME cached
    result instead of spawning again.

    Root cause this closes: `_check_gates_summary_fn` and
    `_check_gate_findings_fn` each independently spawned their OWN full
    `python -m frob check --ticket <id>` (600s timeout apiece) -- and
    every real caller (`_done_report`, `_land`) always wires up BOTH
    closures together, so that duplication cost TWO full, serial
    gate-check subprocess runs on every single done-report/land for
    output that is byte-for-byte re-derivable from ONE run. Passing this
    SAME closure into both `_check_gates_summary_fn`'s and
    `_check_gate_findings_fn`'s `spawn` parameter collapses that back
    down to one spawn total, shared by construction rather than by
    convention -- there is no way for the two consumers to drift back
    into two independent spawns as long as they are handed the same
    `spawn` closure.

    Deliberately module-level, not folded into either consumer: a caller
    that wants only ONE of the two claims still gets the old
    one-spawn-per-consumer behavior for free by passing `spawn=None` (the
    default on both consumers), which makes each build its own private,
    unshared spawn closure exactly as before this ticket.

    T-1703: spawns `--json` now, not plain text -- see
    `_parse_error_findings_from_stdout`'s docstring for why: a regex over
    rendered console prose cannot distinguish "this gate ran and found
    nothing" from "this gate never ran", and cannot parse a diagnostic
    whose renderer does not happen to match the assumed `file:line CODE`
    shape (`ty`'s `file:line:col` is one such miss). `--json` gives every
    consumer the same structured `CheckResult` a regex was standing in
    for.

    T-1344 follow-up (T-2053): this spawn was measured as the
    single largest line item in a typical `frob ticket land` (~209s of a
    ~95-320s land, docs/guides/agent-playbook.md section 13) and
    investigated for a safe speedup CONFINED to this file. Conclusion: no
    safe change exists here alone, and this docstring records why so a
    future reader does not have to re-derive it.

    - `--only`/family-skipping is NOT safe: `_parse_error_findings_from_
      json` counts an `error`-severity diagnostic from ANY `ToolResult`
      (ruff/ty/frob-arch/frob-exports/frob-cycle/frob-dup included, not
      just `gate:*` families) toward the compared claim -- there is no
      stage this spawn could skip without silently narrowing what T-0754
      actually verifies.
    - `--delta` does NOT reduce wall-clock at all -- confirmed by reading
      `check/_python.py`: delta filtering happens to the already-computed
      violation list, after every check still ran in full. It changes
      what is REPORTED, never what is COMPUTED.
    - The `gates/_gate_cache.py` digest-keyed per-gate cache (T-1346,
      on by default) DOES work and DOES matter -- measured directly: two
      consecutive runs against an IDENTICAL, unchanged tree went from
      231s to 150s (35% faster), with the most expensive gate families
      (archgate 32.5s->0.0s, perf 44.8s->0.0s, dead_symbols 12.8s->0.0s,
      pii_structural 11.9s->0.0s, clones 13.0s->0.0s) dropping to
      effectively zero on the cache hit. But this spawn NEVER gets that
      benefit in practice: it always runs against a FRESHLY MERGED tree
      that has never been measured before, and the highest-cost gate
      families read broadly enough across the tree that almost any
      land's own diff intersects their tracked file set, so the cache
      structurally near-always misses at land time even though it is
      genuinely warm-cache-capable in principle.
    - The remaining ~150s floor (identical-tree run, cache fully warm)
      is spent in the ruff/ty/frob-arch/frob-cycle/frob-dup/frob-exports
      lint/static tool layer (`check/_python.py`), which the T-1346 gate
      cache never covers at all -- those tools re-run in full on every
      single invocation, cached or not.

    What WOULD cheapen this, and where it lives (neither is in this
    file, both need a decision from whoever owns them): (1) extend an
    equivalent touched-file digest cache to the lint/static tool layer
    in `check/_python.py`, the largest single remaining floor once the
    existing gate cache is already warm; (2) thread the land's own diff
    (the files actually changed between `pre_land_tip` and the squashed
    tree, already computed inside `src/frob/tickets/_land.py`/
    `_land_cmd.py`) into this spawn as an explicit `--only <affected
    families>` selection, so a small diff only re-verifies the gate/tool
    families whose tracked dependency set it could plausibly have
    touched -- this is the one change that could turn the structural
    near-always-cache-miss above into a near-always-cache-hit, but it
    needs land's diff, which this closure's `root`/`ticket_id`-only
    signature does not have and `_land.py` is out of this ticket's
    scope to change. Separately, `_land_cmd.py`'s `_land_gate_claims_fn`
    (T-1410) runs its OWN comparably-sized `frob check --only gates`
    spawn against `worktree` (not `root`) for the acceptance-criteria
    gate-claim check -- a second, independent cost this investigation
    did not attempt to quantify or fix, since it lives outside this
    file too."""
    cache: dict[str, subprocess.CompletedProcess | None] = {}

    def spawn() -> subprocess.CompletedProcess | None:
        if "result" in cache:
            return cache["result"]
        from frob.app import ticket_runner as _ticket_runner

        guarded = _ticket_runner.guarded_subprocess_run(
            [
                _python_for_tree(root),
                "-m",
                "frob",
                "check",
                "--ticket",
                ticket_id,
                "--json",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "ticket %s: `frob check --ticket %s` refused to spawn (%s)",
                ticket_id,
                ticket_id,
                ProcessGuardError.ExecDisabled,
            )
            cache["result"] = None
        else:
            cache["result"] = guarded.danger_ok
        return cache["result"]

    return spawn


# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:ticket T-0850
# frob:ticket T-0919
# frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds kind="integration"  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree \
# kind="unit"
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn.test_scoped_run_flaky_rule_excluded_from_error_count kind="unit"  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn kind="unit"  # noqa: E501
def _check_gates_summary_fn(  # noqa: ANN201
    root: Path,
    ticket_id: str,
    spawn=None,  # noqa: ANN001
):
    """CLI closure shared by `done-report` capture and `land` re-
    verification (T-0754): calling it spawns a fresh `python -m frob check
    --ticket <id>` in `root` and returns `(errors, warnings, waived)`.
    T-0919: an optional `spawn` (a `_shared_check_spawn_fn(...)` closure)
    lets the caller SHARE that spawn with `_check_gate_findings_fn`
    instead of each parsing its own independent run; defaults to `None`,
    which builds and uses a private one-off spawn (the pre-T-0919
    behavior) so existing standalone callers/tests are unaffected.
    `warnings`/`waived` are the `gate-summary` line's own COUNTS, parsed via
    `_GATE_SUMMARY_COUNTS_RE` (never that line's raw text, whose timing blob
    is nondeterministic -- see the regex's own doc) and never composed or
    retyped by this layer.

    T-0850: `errors` is NOT that raw count -- it is derived from the SAME
    `## Errors` section `_check_gate_findings_fn` parses
    (`_parse_error_findings_from_stdout`), with any `SCOPED_RUN_FLAKY_RULE_
    IDS` finding excluded (`_exclude_scoped_run_flaky`), so the count-only
    fallback `_reverify_done_report_claims_post_merge` uses when neither
    side captured an identity set already excludes the same diff-scoped-
    flaky rules the identity-based comparison excludes -- an asymmetric
    exclusion (identities filtered, counts not) would still let a flaky
    SCOPE001/COV002/TODO001 finding push the raw count up between capture
    and reverify and cause a false refuse. Falls back to the raw gate-
    summary count only when the `## Errors` section itself fails to parse
    (a genuinely unparsable run) but the summary line still did -- keeping
    this closure's previous total-failure semantics unchanged; `warnings`/
    `waived` are deliberately NOT filtered (T-0754/T-0832: only
    `gate_errors` is ever compared).

    Routed through `guarded_subprocess_run` (T-0778's guard) so
    `FROB_DISABLE_EXEC=1` refuses this spawn too. A refused spawn, a hard
    subprocess failure, or unparsable output returns `None` (T-0832) --
    never a `(-1, -1, -1)` sentinel. A real `frob check` run can never
    produce a negative count, but a fixed sentinel is still a VALUE: it
    compares equal to another sentinel of the same shape, which let a
    land re-verification (`_land.py`'s
    `_reverify_done_report_claims_post_merge`) PASS vacuously when both
    the captured claim and the fresh post-merge check were unmeasurable
    for unrelated reasons (the T-0830 incident: a self-closed, lease-
    released ticket's done-report capture and land's own post-merge check
    both failed to run, both recorded `-1`, and `-1 == -1` read as "no
    divergence"). `None` cannot silently compare equal to a measured
    triple, so every caller is forced to branch on "unmeasured"
    explicitly instead."""

    _spawn = spawn if spawn is not None else _shared_check_spawn_fn(root, ticket_id)

    def fn() -> tuple[int, int, int] | None:
        result = _spawn()
        if result is None:
            return None
        data = _parse_check_json(result.stdout)
        if data is None:
            _log.warning(
                "ticket %s: `frob check --ticket %s --json` output was not "
                "parsable JSON (exit=%d) -- gate state is unmeasured, not "
                "zero",
                ticket_id,
                ticket_id,
                result.returncode,
            )
            return None
        findings = _parse_error_findings_from_json(ticket_id, data)
        if findings is None:
            # T-1703: a budget-truncated (or otherwise partial) run
            # already logged its own warning inside
            # `_parse_error_findings_from_json` -- partial coverage
            # cannot back a trustworthy COUNT any more than it can back
            # an identity set, so this claim is unmeasured too, not a
            # smaller number.
            return None
        gate_summary = _find_tool_result(data["results"], "gate-summary")
        summary_text = gate_summary.get("summary", "") if gate_summary else ""
        match = _GATE_SUMMARY_COUNTS_ONLY_RE.search(summary_text)
        if match is None:
            _log.warning(
                "ticket %s: `frob check --ticket %s --json` produced no "
                "gate-summary tool result (exit=%d) -- gate state is "
                "unmeasured, not zero",
                ticket_id,
                ticket_id,
                result.returncode,
            )
            return None
        _raw_errors, warnings, waived = (int(g) for g in match.groups())
        errors = len(_exclude_scoped_run_flaky(findings))
        return (errors, warnings, waived)

    return fn


# frob:ticket T-1703
def _parse_check_json(stdout: str) -> dict | None:
    """`json.loads(stdout)` if it decodes to a dict shaped like a `frob
    check --json` `CheckResult` payload (a `"results"` list present),
    else `None`.

    T-1703: this is the sole gate between "trust this as a structured
    `CheckResult`" and "fall back to nothing" -- deliberately permissive
    about WHAT is in `results` (empty list included: a real, measured
    clean run), strict only about the shape being present at all, so a
    caller that spawned a non-`--json` `frob check` (still a real, live
    caller: `frob.app.ticket_runner._close_cmd`'s T-1399 gate-claim
    check) gets a clean `None` here rather than a crash, and can keep
    using its own legacy text path unaffected by this ticket."""
    import json

    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return None
    return data


# frob:ticket T-1703
def _find_tool_result(results: list, tool_name: str) -> dict | None:  # noqa: ANN001
    """The first `results` entry (a `frob check --json` `ToolResult` dict)
    whose `"tool"` field equals `tool_name`, or `None` if no such entry
    ran this invocation -- e.g. no `"gate-summary"` entry means the gates
    stage itself never ran (an `--only`-scoped call that excluded it), not
    that it ran and found nothing."""
    for r in results:
        if isinstance(r, dict) and r.get("tool") == tool_name:
            return r
    return None


# frob:ticket T-1703
def _budget_deferred_stage_groups(results: list) -> list[str]:  # noqa: ANN001
    """Every stage-group name a `--budget`-bounded `frob check --json` run
    DEFERRED (T-1703's BUDGET001 signal, `frob.app._check_chunking.
    _budget_deferred_result`), parsed straight from the `"budget"` tool
    result's own diagnostic message rather than re-deriving the deferred
    set some other way -- empty if no `"budget"` entry ran at all (every
    selected stage group fit, or `--budget` was never passed)."""
    budget_result = _find_tool_result(results, "budget")
    if budget_result is None:
        return []
    names: list[str] = []
    for diag in budget_result.get("diagnostics", ()):
        if not isinstance(diag, dict) or diag.get("code") != "BUDGET001":
            continue
        message = diag.get("message", "")
        # `_budget_deferred_result`'s own message shape: "BUDGET001:
        # --budget N deferred M stage group(s) to a later run: a, b, c.
        # Resume state persisted -- ...". The `": "` after "BUDGET001"
        # itself is NOT the split point (T-1703 regression: a naive
        # first-`": "` partition stops there, leaving "to a later run: a,
        # b, c" un-split) -- anchor on the literal "to a later run: "
        # phrase instead.
        _prefix, sep, rest = message.partition("to a later run: ")
        if not sep:
            continue
        names_part = rest.split(". Resume state", 1)[0]
        names.extend(n.strip() for n in names_part.split(",") if n.strip())
    return names


# frob:ticket T-0846
# frob:ticket T-0850
# frob:ticket T-1703
def _parse_error_findings_from_json(
    ticket_id: str, data: dict
) -> frozenset[tuple[str, str]] | None:
    """Recover the `frozenset[(rule_id, file)]` identity set from a `frob
    check --json` payload already decoded by `_parse_check_json`, or
    `None` when the run is UNMEASURED -- not "measured zero", not
    "measured some" (T-1703).

    Two independent ways this returns `None`, both closing a real
    incident:

    1. `--budget`-truncated (`_budget_deferred_stage_groups` finds a
       `"budget"` tool result): gates that never ran emit no diagnostics
       at all, so a partial run's `results` list is structurally
       indistinguishable from a genuinely clean full run -- it is a
       DIFFERENT question, not a smaller answer (T-1703's live incident:
       a rolling-baseline sweep recorded `CLEAN, 0 errors` at a commit a
       plain unscoped `frob check` found 5 errors in, 2 of them TICK006
       regressions the same land had just introduced).
    2. No `results` at all, or a run whose exit code and payload disagree
       in a way `_parse_check_json` already rejected as unparsable
       upstream -- callers see this via `_parse_check_json` returning
       `None` before this function is ever reached.

    Every diagnostic across every `ToolResult` with `severity == "error"`
    counts, sourced from the diagnostic's own structured `code`/`file`
    fields -- NOT a regex over that diagnostic's rendered text. This is
    the actual fix for the second T-1703 defect: the old `_GATE_ERROR_
    LINE_RE` text scan assumed every diagnostic renders as `[tag]
    file:line CODE message`, which `ty` (`file:line:col`, an extra
    `:col` the regex's `:\\d+\\s` never matches) and any future renderer
    shape silently violate. Reading `code`/`file` directly off the
    `Diagnostic` model is immune to how any tool chooses to RENDER
    itself, by construction -- there is no shape left to drift out of
    sync with."""
    results = data["results"]
    deferred = _budget_deferred_stage_groups(results)
    if deferred:
        _log.warning(
            "ticket %s: `frob check --json --budget` run deferred %d "
            "stage group(s) (%s) -- error-finding identities are "
            "unmeasured, not a partial set (T-1703: a truncated run is a "
            "DIFFERENT question, never a smaller answer)",
            ticket_id,
            len(deferred),
            ", ".join(deferred),
        )
        return None
    findings: set[tuple[str, str]] = set()
    for r in results:
        if not isinstance(r, dict):
            continue
        for d in r.get("diagnostics", ()):
            if isinstance(d, dict) and d.get("severity") == "error":
                findings.add((d.get("code") or "", d.get("file") or ""))
    return frozenset(findings)


# frob:ticket T-0846
# frob:ticket T-0850
# frob:ticket T-1703
def _parse_error_findings_from_stdout(
    ticket_id: str, stdout: str, returncode: int
) -> frozenset[tuple[str, str]] | None:
    """Recover the `frozenset[(rule_id, file)]` identity set from a fresh
    `frob check <...>` run's captured `stdout`, or `None` when the run is
    unmeasured (T-0846: never a false empty-set claim of "definitely
    zero").

    T-1703: JSON-first. `stdout` is tried as a `frob check --json` payload
    (`_parse_check_json`) and, if it decodes, handed straight to
    `_parse_error_findings_from_json` -- every current in-scope caller of
    this function now spawns `--json` (`_shared_check_spawn_fn`,
    `frob.app.ticket_runner._land_cmd._unscoped_error_findings`), so this
    is the live path in practice. The legacy text-scan below survives
    ONLY for `frob.app.ticket_runner._close_cmd`'s T-1399 gate-claim
    check, which still spawns plain-text `frob check --only gates` and is
    out of this ticket's declared scope -- `stdout` that fails to decode
    as JSON at all falls through to it unchanged from before this ticket,
    same regex, same limitations, not touched here."""
    data = _parse_check_json(stdout)
    if data is not None:
        return _parse_error_findings_from_json(ticket_id, data)
    section = stdout.split("## Errors", 1)
    if len(section) < 2:
        # No "## Errors" heading at all means zero error diagnostics were
        # printed this run (`_section_lines` omits an empty section
        # entirely) -- a real, measured empty set, not "unmeasured": the
        # gate-summary line's own error count (parsed by
        # `_GATE_SUMMARY_COUNTS_RE`) is the cross-check that this is
        # genuinely zero rather than a parse miss.
        if _GATE_SUMMARY_COUNTS_RE.search(stdout) is None:
            _log.warning(
                "ticket %s: `frob check --ticket %s` output had no "
                "parsable gate-summary line at all (exit=%d) -- "
                "error-finding identities are unmeasured, not "
                "necessarily zero",
                ticket_id,
                ticket_id,
                returncode,
            )
            return None
        return frozenset()
    after_heading = section[1].split("\n\n", 1)[0]
    findings: set[tuple[str, str]] = set()
    for line in after_heading.splitlines():
        match = _GATE_ERROR_LINE_RE.match(line)
        if match:
            findings.add((match.group("code"), match.group("file")))
    return frozenset(findings)


# frob:ticket T-0846
# T-0846: one printed error-diagnostic line's shape, e.g.
# "  [gate:SCOPE] src/frob/tickets/_land.py:0  SCOPE001  SCOPE001: message"
# (`frob.check._section_lines`'s `f"  [{tool}] {d.as_text()}"`, `Diagnostic.
# as_text`'s own `file:line  CODE  message` rendering) -- captures the file
# and rule-id code, deliberately not the message (whose wording can change
# without the finding's identity changing). T-1703: legacy fallback only,
# used when `stdout` does not decode as `--json` at all -- see
# `_parse_error_findings_from_stdout`'s docstring.
_GATE_ERROR_LINE_RE = re.compile(
    r"^\s*\[[^\]]*\]\s+(?P<file>\S+?):\d+\s+(?P<code>[A-Za-z][A-Za-z0-9]*)\s"
)


# frob:ticket T-0850
def _exclude_scoped_run_flaky(
    findings: frozenset[tuple[str, str]],
) -> frozenset[tuple[str, str]]:
    """Drop every `(rule_id, file)` pair whose rule is in
    `frob.gates.SCOPED_RUN_FLAKY_RULE_IDS` (T-0850): a diff-scoped rule
    (SCOPE001/COV002/TODO001 today) can appear or disappear between two
    SCOPED `--ticket` checks taken at different times purely from base
    drift, not a real regression -- comparing these identities at all
    reintroduces the exact false-`ClaimDivergence` failure mode T-0846
    already closed for the raw-count case. Applied at the single shared
    parse both `_check_gate_findings_fn` and `_check_gates_summary_fn`
    call, so capture time (done-report) and reverify time (land) exclude
    the same rules symmetrically by construction -- an asymmetric filter
    (excluding only at one end) would still diverge on pure drift noise."""
    from frob.gates import SCOPED_RUN_FLAKY_RULE_IDS

    return frozenset(
        (rule, file) for rule, file in findings if rule not in SCOPED_RUN_FLAKY_RULE_IDS
    )


# frob:ticket T-0846
# frob:ticket T-0919
# frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds kind="integration"  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn.test_scoped_run_flaky_rule_excluded_from_findings kind="unit"  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn.test_default_spawn_none_keeps_each_closure_independent kind="unit"  # noqa: E501
def _check_gate_findings_fn(  # noqa: ANN201
    root: Path,
    ticket_id: str,
    spawn=None,  # noqa: ANN001
):
    """CLI closure (T-0846, sibling to `_check_gates_summary_fn`): calling it
    spawns a fresh `python -m frob check --ticket <id>` in `root` and
    returns a `frozenset[(rule_id, file)]` recovered from every `## Errors`
    diagnostic line the run printed, MINUS any finding under a
    `SCOPED_RUN_FLAKY_RULE_IDS` rule (T-0850: `_exclude_scoped_run_flaky`)
    -- the per-finding IDENTITY set `_reverify_done_report_claims_post_merge`
    compares instead of a raw count, closing the masking gap a scope-wide
    count alone cannot close (a land's own diff introducing N new errors
    sailing through whenever an unrelated fix on the same branch removed
    more than N). Routed through `guarded_subprocess_run` (T-0778's guard),
    same as `_check_gates_summary_fn`. A refused spawn or a hard subprocess
    failure returns `None` (unmeasured, never an empty-set false claim of
    "definitely zero") -- `_reverify_done_report_claims_post_merge` falls
    back to the count-only comparison in that case.

    T-0919: an optional `spawn` (a `_shared_check_spawn_fn(...)` closure)
    lets the caller SHARE that one spawn with `_check_gates_summary_fn`
    instead of each running its own independent `frob check --ticket`
    (the doubled-cost tradeoff this docstring used to document as a known
    follow-up -- now closed: `_done_report`/`_land` both pass the SAME
    shared spawn to both closures). Defaults to `None`, which builds a
    private one-off spawn (the pre-T-0919 behavior) so existing standalone
    callers/tests are unaffected."""

    _spawn = spawn if spawn is not None else _shared_check_spawn_fn(root, ticket_id)

    def fn() -> frozenset[tuple[str, str]] | None:
        result = _spawn()
        if result is None:
            return None
        findings = _parse_error_findings_from_stdout(
            ticket_id, result.stdout, result.returncode
        )
        if findings is None:
            return None
        return _exclude_scoped_run_flaky(findings)

    return fn


# frob:ticket T-0754
def _run_tests_count_fn(root: Path):  # noqa: ANN201
    """CLI closure shared by `done-report` capture and `land` re-
    verification (T-0754): calling it with a sequence of non-cmd evidence
    node ids actually RUNS them (reusing `_verify_ids_passing`, D-01's
    same real-run verification) and returns the count that ACTUALLY
    passed -- never the length of the input, so a divergence between
    "claimed" and "actually ran" is visible even when every id still
    resolves."""

    def fn(node_ids: Sequence[str]) -> int:
        if not node_ids:
            return 0
        from frob.app import ticket_runner as _ticket_runner

        collected = _ticket_runner._collect_python_and_rust_ids(root)
        if collected.is_err:
            _log.warning(
                "ticket: capture collection failed (%s) -- treating all %d "
                "evidence id(s) as not passing",
                collected.danger_err,
                len(node_ids),
            )
            return 0
        python_ids, rust_ids, runners = collected.danger_ok
        from frob.app import ticket_runner as _ticket_runner

        passing = _ticket_runner._verify_ids_passing(
            root, node_ids, python_ids, rust_ids, runners
        )
        return len(passing)

    return fn


# frob:ticket T-0458
# frob:ticket T-0754
# frob:tests \
# tests/test_tickets_evidence_cli.py::TestDoneReportCli.test_cli_composes_and_writes
def _done_report(root: Path, cfg: AppConfig) -> None:
    """`frob ticket done-report <id> (--why TEXT | --why-file PATH | -)`:
    resolve the narrative why, then call `frob.tickets.set_done_report` --
    the ONLY thing this command does is supply `why`; the Changed and
    Evidence sections are composed entirely inside `set_done_report` from
    git and the ticket's own recorded evidence, never parsed/typed here
    (T-0458).

    T-0754: also supplies `run_tests`/`check_gates` (`_run_tests_count_fn`/
    `_check_gates_summary_fn`) so `set_done_report` captures a real
    `### Captured claims` section -- a test count from actually running
    the ticket's own evidence and a gate-state summary from a fresh `frob
    check --ticket`, neither typed by the agent -- instead of leaving the
    Done report's test/gate claims as unverified free prose."""
    from frob.tickets import set_done_report

    if cfg.ticket_id is None:
        _log.error("frob ticket done-report requires <id>")
        sys.exit(1)

    why = _resolve_done_report_why(cfg)
    if why is None:
        _log.error(
            "frob ticket done-report requires --why TEXT, --why-file PATH, "
            "or a narrative piped via stdin"
        )
        sys.exit(1)

    # T-0919: one shared spawn feeds BOTH check_gates/check_gate_findings
    # below instead of each running its own full `frob check --ticket`.
    _shared_spawn = _shared_check_spawn_fn(root, cfg.ticket_id)
    result = set_done_report(
        root,
        cfg.ticket_id,
        why=why,
        base_ref=cfg.ticket_base_ref,
        run_tests=_run_tests_count_fn(root),
        check_gates=_check_gates_summary_fn(root, cfg.ticket_id, spawn=_shared_spawn),
        check_gate_findings=_check_gate_findings_fn(
            root, cfg.ticket_id, spawn=_shared_spawn
        ),
    )
    if result.is_err:
        _log.error("done-report failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: Done report written (%d evidence id(s) rendered)",
        cfg.ticket_id,
        len(ticket.evidence),
    )

    # frob:ticket T-1178
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): {cfg.ticket_id} Done report",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-0737


def _collect_python_and_rust_ids(root: Path):  # noqa: ANN201
    """`(python_ids, rust_ids, runners)` -- the same union-collection dance
    `_apply_evidence` always did (T-0301), factored out so both evidence
    recording (D-01 pass-check) and `frob ticket land`'s post-merge
    re-verification (D-05) share one implementation. Returns `Err` only on
    a python collection failure (rust degrades to a WARNING + empty set,
    matching the existing resilience posture); `runners` is `()` if
    `load_runners` itself fails."""
    from frob.testing import collect_python_tests, collect_rust_tests, load_runners

    collected = collect_python_tests(root)
    if collected.is_err:
        return collected

    python_ids = frozenset(collected.danger_ok.node_ids)
    rust_ids: frozenset[str] = frozenset()

    runners = load_runners(root)
    runner_specs = runners.danger_ok if runners.is_ok else ()
    if any(spec.language == "rust" for spec in runner_specs):
        rust_collected = collect_rust_tests(root)
        if rust_collected.is_err:
            _log.warning(
                "ticket evidence: rust collection failed (%s); validating "
                "against pytest ids only for this call",
                rust_collected.danger_err,
            )
        else:
            rust_ids = frozenset(rust_collected.danger_ok.node_ids)

    from typani.result import Ok

    return Ok((python_ids, rust_ids, runner_specs))


# frob:ticket T-0398
def _verify_ids_passing(
    root: Path,
    node_ids,  # noqa: ANN001
    python_collected: frozenset[str],
    rust_collected: frozenset[str],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """D-01 CLI wiring: actually RUN `node_ids` (bucketed by which
    collected set each id resolves against, python vs rust) and return the
    subset that passed -- the piece that makes `frob ticket evidence`/
    `close`/`land` mean "the work was actually tested," not just "a test
    with this name exists."

    Each language bucket is run as its OWN `run_selected` call, not one
    combined invocation, for two reasons: (1) a combined run's single exit
    code cannot tell you WHICH of several ids failed, so a batch mixing a
    red and a green id would have to reject both -- overly strict for no
    reason; per-language buckets are the coarsest split that still lets
    genuinely-independent ids pass independently. (2) an infra failure in
    one language (e.g. no PyO3 env for rust) must not silently swallow a
    python id's real, successful verification -- each bucket's own
    Err/failure is logged and only THAT bucket's ids are withheld from the
    returned passing set, never the whole call. An id that resolves
    against neither collected set is simply absent from the result (it
    already fails resolution elsewhere; this function only concerns
    itself with ids that at least exist).

    T-0856: a bucket itself is no longer all-or-nothing either -- when the
    bucket's OWN single batched run comes back not-ok (but the run
    executed, i.e. not an infra error),
    `_reverify_failing_bucket_individually` reruns each id in that bucket
    on its own so only the genuinely-failing id(s) are withheld, not every
    id that happened to share a batch with one (the T-0588 incident: 36
    evidence ids in one batch, one flake, land reported all 36 as failing).
    A per-id failure that resolves to a currently-quarantined node id
    (T-0575) does not veto either."""
    from frob.tickets._models import matches_collected

    passing: set[str] = set()
    buckets = {
        "python": tuple(n for n in node_ids if matches_collected(n, python_collected)),
        "rust": tuple(n for n in node_ids if matches_collected(n, rust_collected)),
    }
    for language, items in buckets.items():
        if items:
            passing.update(_verify_one_bucket_passing(root, language, items, runners))
    return frozenset(passing)


# frob:ticket T-0398
# frob:ticket T-0856
def _verify_one_bucket_passing(
    root: Path,
    language: str,
    items: tuple[str, ...],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """One language bucket of `_verify_ids_passing`'s work: run `items`
    via ONE batched `run_selected` call first (the cheap common case, all
    green); on any failure, `_reverify_failing_bucket_individually` (T-0856)
    attributes the failure to only the ids that genuinely fail on their
    OWN rerun, so one order-dependent/flaky id can no longer misattribute
    a whole multi-id batch (up to a ticket's entire evidence set, T-0588's
    36-id incident) as failing. Falls back to a direct `pytest <ids>`
    invocation for python when no `[[test.runner]]` is declared at all --
    `frob.toml` is optional, so a repo that never configured one must not
    fall straight to "not passing" (a false-positive trap this fix was
    explicitly warned against)."""
    from frob.testing import SelectionReport, TestingError, run_selected

    selection = SelectionReport(
        touched=(),
        selected={language: items},
        ripple=(),
        unbound=(),
        fallback="evidence-verify",
    )
    run = run_selected(selection, runners, root)
    if run.is_ok and run.danger_ok.ok:
        return frozenset(items)
    if run.is_err and language == "python" and run.danger_err == TestingError.NoRunner:
        if _run_pytest_directly(root, items):
            return frozenset(items)
        if len(items) > 1:
            return _reverify_direct_pytest_individually(root, items)
        _log.warning(
            "ticket evidence: direct pytest verification FAILED for %s", list(items)
        )
        return frozenset()
    if run.is_ok and len(items) > 1:
        # T-0856: the batch itself executed (no infra error) but at least
        # one id failed -- do NOT blame the whole bucket; find out which
        # id(s) genuinely fail on their own.
        return _reverify_failing_bucket_individually(root, language, items, runners)
    _log.warning(
        "ticket evidence: %s verification %s for %s",
        language,
        f"run failed to execute ({run.danger_err})" if run.is_err else "run FAILED",
        list(items),
    )
    return frozenset()


# frob:ticket T-0856
def _reverify_failing_bucket_individually(
    root: Path,
    language: str,
    items: tuple[str, ...],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """T-0856: a batched `run_selected` call over `items` came back not-ok
    -- rerun EACH id on its own (bounded to this one bucket, only paid on
    the already-uncommon failing-batch path) so a single order-dependent
    or genuinely-flaky id cannot misattribute failure to every other id in
    the same batch (the T-0588 incident: 36 evidence ids ran as one batch,
    one documented flake failed, land reported all 36 as not passing).

    A per-id failure that resolves to a currently-quarantined node id
    (`frob.testing._stability.quarantined_node_ids`, T-0575) is still
    counted as PASSING here: a quarantined flake is not supposed to veto a
    land/evidence check by design (T-0635 wires quarantine into `frob
    test` proper -- this is read-only consumption of that same state, not
    a reimplementation of it). A stability-tracking read failure (no
    `.frob/stability.json` yet, or any other load error) degrades to an
    empty quarantine set -- fail-closed on the underlying pass/fail check,
    never silently permissive just because quarantine state is
    unavailable."""
    from frob.testing import SelectionReport, run_selected
    from frob.testing._stability import load_stability, quarantined_node_ids

    quarantined = quarantined_node_ids(load_stability(root))
    passing: set[str] = set()
    for item in items:
        selection = SelectionReport(
            touched=(),
            selected={language: (item,)},
            ripple=(),
            unbound=(),
            fallback="evidence-verify-individual",
        )
        run = run_selected(selection, runners, root)
        if run.is_ok and run.danger_ok.ok:
            passing.add(item)
        elif item in quarantined:
            _log.warning(
                "ticket evidence: %s %s failed individually but is "
                "quarantined (T-0575) -- not counted as a veto",
                language,
                item,
            )
            passing.add(item)
        else:
            _log.warning(
                "ticket evidence: %s %s FAILED individually (not quarantined)",
                language,
                item,
            )
    return frozenset(passing)


# frob:ticket T-0398
_WORKTREE_LEASE_ENV_VARS = ("FROB_WORKTREE", "FROB_AGENT")
"""Env vars set by the worktree-lease mechanism (docs/guides/agent-playbook.md
section 1/3) that must never leak into a spawned verification pytest process
-- see `_run_pytest_directly`'s docstring for why (T-0884)."""


# frob:ticket T-0884
# frob:tests tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv.test_strips_worktree_and_agent_env  # noqa: E501
# frob:tests tests/test_ticket_runner_pytest_env.py::TestRunPytestDirectlyStripsLeaseEnv.test_missing_lease_env_is_fine  # noqa: E501
def _run_pytest_directly(root: Path, node_ids) -> bool:  # noqa: ANN001
    """`uv run pytest <node_ids> -q -o addopts=` in `root`, exit 0 == pass
    -- the no-`[[test.runner]]`-declared fallback `_verify_ids_passing`
    uses so D-01 verification works even in a repo that never configured
    `frob.toml`'s test-runner registry (the same posture
    `collect_python_tests` already takes for collection).

    Spawns with the CALLER's `FROB_WORKTREE`/`FROB_AGENT` lease env
    stripped (T-0884): those two vars are set on the recording agent's own
    process so every `frob ticket` invocation it makes is attributed to its
    leased worktree, but they have no business governing the test process
    THIS call spawns to verify a ticket's own node ids -- a test under
    verification that itself does real git worktree operations against a
    throwaway `tmp_path` fixture repo (e.g. `tests/test_ticket_land.py`)
    would otherwise be refused by
    `frob.tickets._worktree_guard.enforce_worktree_lease`, which sees the
    recorder's lease pointing at an unrelated path and blocks the test's
    own, legitimate mutation."""
    argv = ("uv", "run", "pytest", *node_ids, "-q", "-o", "addopts=")
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _WORKTREE_LEASE_ENV_VARS
    }
    try:
        from frob.app import ticket_runner as _ticket_runner

        guarded = _ticket_runner.guarded_subprocess_run(
            list(argv),
            cwd=str(root),
            capture_output=True,
            timeout=300.0,
            text=True,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning(
            "ticket evidence: direct pytest failed to spawn in %s: %s", root, exc
        )
        return False
    if guarded.is_err:
        _log.warning("ticket evidence: direct pytest failed to spawn in %s", root)
        return False
    return guarded.danger_ok.returncode == 0


# frob:ticket T-0856
def _reverify_direct_pytest_individually(
    root: Path, items: tuple[str, ...]
) -> frozenset[str]:
    """T-0856's per-id attribution fix, for the no-`[[test.runner]]`-
    declared direct-pytest fallback path (`_run_pytest_directly`'s own
    batch call already failed): rerun each id on its own via the same
    direct `uv run pytest` invocation, and consult the stability
    quarantine (`frob.testing._stability.quarantined_node_ids`, T-0575) the
    same way `_reverify_failing_bucket_individually` does for the runner-
    based path, so this fallback does not regress to the pre-T-0856 all-
    or-nothing misattribution just because no `[[test.runner]]` happens to
    be configured."""
    from frob.testing._stability import load_stability, quarantined_node_ids

    quarantined = quarantined_node_ids(load_stability(root))
    passing: set[str] = set()
    for item in items:
        if _run_pytest_directly(root, [item]):
            passing.add(item)
        elif item in quarantined:
            _log.warning(
                "ticket evidence: direct pytest %s failed individually but "
                "is quarantined (T-0575) -- not counted as a veto",
                item,
            )
            passing.add(item)
        else:
            _log.warning(
                "ticket evidence: direct pytest %s FAILED individually "
                "(not quarantined)",
                item,
            )
    return frozenset(passing)


# frob:ticket T-0106
# frob:ticket T-0398
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_evidence(
    root: Path,
    ticket_id: str,
    node_ids: list[str],
    accepts: list[int] | None = None,
):
    """Collect pytest node ids, validate `node_ids` against them AND
    actually run them (D-01: `passed`) via `frob.tickets.add_evidence`
    (resolvable-id + passing + dedupe semantics, wholesale batch rejection
    on any unresolvable OR non-passing id), and append the resolvable
    passing ones to `ticket_id`'s structured evidence list. Shared by
    `frob ticket evidence`, `frob ticket new --evidence`, and `frob ticket
    close --evidence` so all three routes go through identical validation
    -- never through an ad hoc, unvalidated write. Returns the
    `add_evidence` Result unchanged so callers (e.g. `_close`) can refuse
    to transition state on failure.

    `accepts` (T-0572) threads straight through to `add_evidence`'s own
    `accepts`: 0-based `ticket.acceptance` indices `node_ids` also bind to,
    in the same write. `None`/empty binds nothing (the pre-T-0572 default).

    T-0301 (feldspar T-0015 escalation): a `--evidence` id must resolve
    against the union of every collected oracle the repo's `[[test.runner]]`
    entries declare, not pytest alone -- a rust node id IS collected (via
    `collect_rust_tests`, into `.frob/cargo-collect.json`) whenever
    `frob.toml` declares a `language = "rust"` runner, so it must be part of
    the same oracle set pytest ids validate against. Rust collection is
    attempted only when a rust runner is actually configured (repos with no
    rust runner never pay a `cargo` invocation here), and a rust-collection
    failure degrades to a WARNING plus python-only validation rather than
    blocking evidence recording outright -- an unrelated cargo/pyo3
    environment problem must not stop a purely-python ticket's evidence
    from being recorded (same resilience posture as T-0144's `make core`
    guidance elsewhere in this module).

    T-0398: this is the CLI's STRICT default -- `passed` is always
    computed and always passed to `add_evidence`, so a red/errored/
    skipped evidence test rejects the whole batch (`EvidenceNotPassing`)
    through the real `frob ticket evidence`/`close` commands, not just the
    library function a caller could otherwise bypass by never supplying
    `passed`.

    T-0492: `node_ids` is normalized (`normalize_evidence_separator`, the
    SAME dot-to-`::` rewrite `add_evidence`'s own `_validate_evidence_list`
    applies, T-0293) BEFORE it is handed to `_verify_ids_passing` here --
    not after. `_verify_ids_passing` buckets ids via `matches_collected`
    against `python_ids`/`rust_ids`, which only ever contain pytest's
    native `::`-form node ids; a raw dot-form id (`path::Class.method`,
    the canonical spelling this module's own docs teach) never matches
    either bucket, so its "did it pass" check silently runs on an empty
    selection and the id ends up absent from `passing` -- rejected
    downstream as `EvidenceNotPassing` even though the test genuinely
    passed. Passing the SAME normalized list into both the passing-check
    and `add_evidence` keeps the two normalization paths from silently
    diverging again."""
    from frob.app import ticket_runner as _ticket_runner
    from frob.tickets import add_evidence, normalize_evidence_separator

    collected = _ticket_runner._collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.error(
            "ticket evidence: pytest collection failed: %s", collected.danger_err
        )
        return collected
    python_ids, rust_ids, runners = collected.danger_ok
    collected_ids = python_ids | rust_ids

    normalized_ids = [normalize_evidence_separator(n) for n in node_ids]
    from frob.app import ticket_runner as _ticket_runner

    passing = _ticket_runner._verify_ids_passing(
        root, normalized_ids, python_ids, rust_ids, runners
    )

    result = add_evidence(
        root, ticket_id, normalized_ids, collected_ids, passed=passing, accepts=accepts
    )
    _log_evidence_result(ticket_id, result)
    return result


# frob:ticket T-1537
# frob:tests tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli.test_cli_replaces_and_commits  # noqa: E501
# frob:ticket T-1733
def _resolve_evidence_replace_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket evidence --replace`'s `--reason` (T-1733):
    `--reason-file` wins if given (read verbatim -- T-0737, same
    rationale as `_resolve_scope_reason`), else the inline `--reason`
    string. Exits 1 if both are given; returns `None` if neither is
    given (the caller reports the "one is required" error, matching
    `_resolve_scope_reason`'s own shape)."""
    if (
        cfg.ticket_evidence_replace_reason_file is not None
        and cfg.ticket_evidence_replace_reason
    ):
        _log.error(
            "ticket evidence --replace: --reason and --reason-file are "
            "mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_evidence_replace_reason_file is not None:
        try:
            return cfg.ticket_evidence_replace_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket evidence --replace: could not read --reason-file %s: %s",
                cfg.ticket_evidence_replace_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_evidence_replace_reason


# frob:ticket T-1733
def _apply_replace_evidence(
    root: Path,
    ticket_id: str,
    replace_pair: list[str],
    *,
    reason: str,
    archived: bool = False,
):  # noqa: ANN201
    """CLI wiring for `frob ticket evidence <id> --replace OLD NEW
    (--reason TEXT | --reason-file PATH)` (T-1537, `reason` required as
    of T-1733): resolves the SAME `python_ids`/`rust_ids`/`passing`
    oracle `_apply_evidence` uses (so a `--replace` target is held to the
    exact same "must resolve, must pass" bar a fresh `add_evidence` id
    is) and calls `frob.tickets.replace_evidence`, the single-writer path
    that updates the flat evidence list AND every acceptance binding
    atomically. `replace_pair` is the CLI's own `[old, new]` 2-element
    list (`nargs=2`). `archived` (T-1561, `--archived`) retargets the
    load/write at archive storage instead of active -- see
    `replace_evidence`'s own `archived` parameter."""
    from frob.app import ticket_runner as _ticket_runner
    from frob.tickets import normalize_evidence_separator, replace_evidence

    old_node, new_node = replace_pair
    collected = _ticket_runner._collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.error(
            "ticket evidence --replace: pytest collection failed: %s",
            collected.danger_err,
        )
        return collected
    python_ids, rust_ids, runners = collected.danger_ok
    collected_ids = python_ids | rust_ids

    normalized_new = normalize_evidence_separator(new_node)
    passing = _ticket_runner._verify_ids_passing(
        root, [normalized_new], python_ids, rust_ids, runners
    )

    result = replace_evidence(
        root,
        ticket_id,
        old_node,
        new_node,
        collected_ids,
        passed=passing,
        reason=reason,
        archived=archived,
    )
    if result.is_err:
        _log.error("ticket evidence --replace failed: %s", result.danger_err)
    else:
        _log.info(
            "%s: evidence --replace %r -> %r applied (%d evidence id(s))",
            ticket_id,
            old_node,
            new_node,
            len(result.danger_ok.evidence),
        )
    return result


def _log_evidence_result(ticket_id: str, result) -> None:  # noqa: ANN001
    """Log `add_evidence`'s outcome: the failure reason + remedy, or the
    ticket's resulting evidence id count."""
    if result.is_err:
        _log.error(
            "ticket evidence failed: %s (the collection cache self-refreshes "
            "on the next `frob test` / `frob check` run; if it still does "
            "not resolve, delete .frob/pytest-collect.json (or "
            ".frob/cargo-collect.json for rust) to force a rebuild, or fix "
            "the id)",
            result.danger_err,
        )
        return

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d id(s): %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )


# frob:ticket T-0215
# frob:ticket T-0796
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_cmd_evidence(
    root: Path, ticket_id: str, command: str, accepts: Sequence[int] | None = None
):
    """Run `command` via `frob.tickets.add_cmd_evidence` and append its
    exit-status/digest entry to `ticket_id`'s evidence list -- the
    docs/design-kind non-pytest evidence channel (T-0215). Returns the
    `add_cmd_evidence` Result unchanged so callers (`_close`, `_evidence`)
    can refuse to transition state on failure, the same contract
    `_apply_evidence` gives pytest-node-id evidence.

    `accepts` (T-0796) is threaded straight through to `add_cmd_evidence`
    so `--accepts` binds cmd evidence onto the named acceptance criteria
    exactly like it already does for pytest-node evidence via
    `_apply_evidence` -- before this, both call sites below dropped
    `cfg.ticket_accepts` for the cmd-evidence path, so a docs-kind ticket
    closed with `--evidence-cmd` + `--accepts` silently ended up UNBOUND."""
    from frob.tickets import add_cmd_evidence

    result = add_cmd_evidence(root, ticket_id, command, accepts)
    if result.is_err:
        _log.error(
            "ticket evidence-cmd failed: %s (docs-kind tickets only; code "
            "kinds require pytest --evidence node ids)",
            result.danger_err,
        )
        return result

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d entries: %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )
    return result


# frob:ticket T-0096
# frob:ticket T-0810
