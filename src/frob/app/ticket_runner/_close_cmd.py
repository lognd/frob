"""frob.app.ticket_runner._close_cmd -- the `close`/`reverify`/`review`/
`fail`/`drop` command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/ scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim -- \
# carried from the pre-T-1089-split monolith's identical file-level waiver \
# (frob.app.ticket_runner/__init__.py)"

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

from ._lifecycle import _load_ticket_or_exit
from ._verify import (
    _apply_cmd_evidence,
    _apply_evidence,
    _check_gate_findings_fn,
    _check_gates_summary_fn,
    _run_tests_count_fn,
    _shared_check_spawn_fn,
)

_CACHE_REL = Path(".frob") / "cache.db"

_log = get_logger("frob.app.ticket_runner")


def _close_failure_hint(ticket_id: str, state, err, *, verb: str = "close") -> str:  # noqa: ANN001
    """The log message for a failed close: names a concrete remedy instead of
    just echoing the raw error (T-0215 -- both close-on-queued's
    InvalidTransition and MissingEvidence used to log with no next step).

    T-1005: `verb` (default `"close"`) lets `frob ticket reverify` share
    this exact remedy text under its own name (`"reverify"`) instead of
    forking a second copy that could drift -- the remedies themselves
    (start first, add evidence, bind acceptance, get an approved review,
    strengthen mutation-killing tests) are identical for both commands,
    only the failing verb differs."""
    from frob.tickets import TicketError, TicketState

    if err == TicketError.InvalidTransition and state in (
        TicketState.QUEUED,
        TicketState.PLANNED,
    ):
        return (
            f"{verb} failed: {err} -- {ticket_id} is {state.value}, not "
            f"in-progress -- run `frob ticket start {ticket_id}` first"
        )
    if err == TicketError.MissingEvidence:
        return (
            f"{verb} failed: {err} -- {ticket_id} is missing evidence or a "
            f"Done report -- add evidence (`frob ticket evidence {ticket_id} "
            f"<node-id>...`, or for a docs-kind ticket `--evidence-cmd "
            f"'<command>'`) and write a '## Done report' heading under "
            f"{ticket_id}'s section in tickets.md"
        )
    if err == TicketError.AcceptanceUnbound:
        return (
            f"{verb} failed: {err} -- see the WARNING line above naming "
            f"which acceptance criterion/criteria still have no resolving "
            f"evidence id; bind one with `frob ticket evidence {ticket_id} "
            f"<node-id> --accepts <index>` (0-based, per "
            f"`frob ticket show {ticket_id}`'s acceptance list)"
        )
    if err == TicketError.MissingApprovedReview:
        return (
            f"{verb} failed: {err} -- {ticket_id} needs an approve-verdict "
            f"review naming the current commit (`frob ticket review "
            f"{ticket_id} --verdict approve --reviewer NAME --findings-file "
            f"PATH`) before `--strict` will succeed"
        )
    if err == TicketError.EvidenceConfirmatoryOnly:
        return (
            f"{verb} failed: {err} -- see the WARNING TEST016 line(s) above "
            f"naming the exact file:line + mutation the bound evidence "
            f"never killed; strengthen those tests, then retry `frob "
            f"ticket {verb} {ticket_id}`, or if this is a genuine false "
            f"positive retry with `frob ticket {verb} {ticket_id} "
            f"--skip-mutation-evidence` (logs a loud, justification-"
            f"required override, does not suppress the finding)"
        )
    return f"{verb} failed: {err}"


# frob:ticket T-0398
def _covers_scope_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """D-02 CLI wiring: whether `ticket`'s evidence covers a touched/scope
    symbol, via `frob.gates.evidence_covers_scope` over the current graph.

    Returns `None` (skip the check entirely) when `ticket` carries NO
    non-cmd evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest verification
    channel (`add_cmd_evidence`) that already substitutes for "coverage";
    `evidence_covers_scope` would otherwise (correctly, by its own
    contract) return `False` for a ticket with zero non-cmd evidence to
    scan, which would wrongly block the docs cmd-evidence path this ticket
    was explicitly warned not to break. Also returns `None` when
    `ticket.scope` itself is empty -- an undeclared scope gives the
    binding check nothing to bind AGAINST, so "does evidence cover scope"
    is not a meaningful question to ask (this is a false-positive guard,
    not a loophole: a ticket that declares a real scope still gets the
    full check). Returns `False` (fail-closed, blocking the close) if the
    graph itself cannot be loaded/built -- "cannot verify" must never
    silently become "verified"."""
    from frob.gates import evidence_covers_scope
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd or not ticket.scope:
        return None

    from frob.app import ticket_runner as _ticket_runner

    snapshot = _ticket_runner._graph_snapshot(root)
    if snapshot.is_err:
        _log.warning(
            "ticket close: graph unavailable (%s), cannot verify D-02 "
            "scope-binding -- refusing to close on unverifiable evidence",
            snapshot.danger_err,
        )
        return False
    return evidence_covers_scope(ticket, snapshot.danger_ok)


# frob:ticket T-0844
def _close_mutation_evidence_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """T-0844: whether `ticket` carries an unwaived ERROR-severity TEST016
    confirmatory-only-evidence finding, mirroring `frob.tickets._land.
    _check_mutation_evidence`'s land-time computation
    (`frob.gates.mutation_evidence_violations`) so `frob ticket close` (the
    direct, non-land path) is not exempt from the same obligation.

    There is no separate worktree/base_ref split on the close path the way
    `land` has (close runs against the CURRENT checkout, not a merge of a
    worktree onto main) -- `root` doubles as both the tree scanned and the
    diff base's own checkout, and `current_branch(root)` supplies the base
    ref the diff is scoped against, same as `_land_precheck` does for
    `land`. Returns `None` (skip the check) when the branch cannot be
    resolved -- "cannot verify" must never silently become "verified", but
    this check is additive to the pre-existing evidence gates (T-0755's own
    posture), so it degrades to a no-op rather than fail-closed here."""
    from frob.gates import mutation_evidence_violations
    from frob.gitio import current_branch

    branch = current_branch(root)
    if branch.is_err:
        _log.warning(
            "ticket close: %s could not resolve current branch, skipping "
            "TEST016 mutation-evidence check",
            ticket.id,
        )
        return None
    violations = mutation_evidence_violations(root, ticket, branch.danger_ok)
    for v in violations:
        _log.warning("ticket close: %s TEST016 %s", ticket.id, v.message)
    errors = [v for v in violations if v.severity == "error"]
    return not errors if violations else None


# frob:ticket T-1410
def _matching_gate_claim_files(
    findings: frozenset[tuple[str, str]], rule: str, glob: str
) -> list[str]:
    """The sorted list of files in `findings` (a `(rule_id, file)` identity
    set) that match `rule` and `fnmatch` against `glob` -- split out of
    `_close_gate_claims_for_ticket`'s per-criterion loop (PERF004: a
    `sorted()` call textually inside a `for` loop body) so the sort lives
    in its own single-purpose function instead of inline in the loop."""
    from fnmatch import fnmatch

    return sorted(f for r, f in findings if r == rule and fnmatch(f, glob))


# frob:ticket T-1410
def _close_gate_claims_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """T-1410 CLI wiring: whether every acceptance criterion on `ticket`
    shaped as a package-wide gate-outcome claim ("0 <RULE> findings under
    <glob>", `frob.tickets._evidence._gate_claim_criteria`) actually holds
    against a live `frob check --only gates` run -- the T-1276 defect this
    closes: T-1276's own criterion [0] read "0 TEST005 findings under
    src/frob/app/**", was bound to unrelated passing evidence ids, and
    closed done (LAND-PROOF verified) against 116 live TEST005 findings
    under that exact glob, because nothing computed `gate_claims_verified`
    -- the T-1399 guard clause existed but had no live caller.

    Returns `None` (skip the check) when `ticket` carries no criterion in
    this shape at all -- `_gate_claim_criteria` returning `()` means the
    `gate_claims_verified` guard this feeds is a no-op regardless of what
    is injected, so a ticket with only ordinary criteria is unaffected.

    `frob check` has no CLI-level path-glob filter for gate violations (the
    positional `path` argument scopes the ruff/ty/pytest tool stages, not
    the `gates` stage's own violation set) -- so "scoped to the glob" here
    means running ONLY the `gates` stage (not the full ruff/ty/pytest/gates
    pipeline `_check_gate_findings_fn` runs for the Done-report recap) and
    then filtering the returned `(rule, file)` finding-identity set by
    `fnmatch` against the criterion's glob, once per criterion, rather than
    narrowing what actually runs. Measured ~113s wall for a full `--only
    gates` pass on this repo (docs comment on `frob.check._STAGE_GROUPS`) --
    slow enough to be worth naming, not slow enough to skip; this spawn
    carries its own 600s subprocess timeout (matching every other
    `guarded_subprocess_run` call in this module), independent of any
    foreground/session-level cap.

    Returns `False` (fail-closed, blocking the close) if the spawn is
    refused or its output is unparsable -- "cannot verify" must never
    silently become "verified", the same posture `_covers_scope_for_
    ticket`/`_reverify_evidence_for_close` already take for their own
    unloadable/uncollectable failure modes."""
    from frob.tickets._evidence import _criterion_gate_claim, _gate_claim_criteria

    claims = _gate_claim_criteria(ticket)
    if not claims:
        return None

    from frob.app import ticket_runner as _ticket_runner

    spawned = _ticket_runner.guarded_subprocess_run(
        [
            _ticket_runner._python_for_tree(root),
            "-m",
            "frob",
            "check",
            "--only",
            "gates",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if spawned.is_err:
        _log.warning(
            "ticket close: %s `frob check --only gates` refused to spawn "
            "(%s) -- cannot verify T-1399 gate-claim criteria, refusing to "
            "close on unverifiable evidence",
            ticket.id,
            spawned.danger_err,
        )
        return False
    proc = spawned.danger_ok
    findings = _ticket_runner._parse_error_findings_from_stdout(
        ticket.id, proc.stdout, proc.returncode
    )
    if findings is None:
        _log.warning(
            "ticket close: %s `frob check --only gates` output had no "
            "parsable gate-summary line -- cannot verify T-1399 gate-claim "
            "criteria, refusing to close on unverifiable evidence",
            ticket.id,
        )
        return False

    all_clean = True
    for c in claims:
        parsed = _criterion_gate_claim(c.text)
        if parsed is None:
            continue
        rule, glob = parsed
        matches = _matching_gate_claim_files(findings, rule, glob)
        if matches:
            _log.warning(
                "ticket close: %s criterion %r unmet -- %d live %s "
                "finding(s) under %s: %s",
                ticket.id,
                c.text,
                len(matches),
                rule,
                glob,
                matches,
            )
            all_clean = False
    return all_clean


# frob:ticket T-1387
def _close_own_obligations_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """T-1387 CLI wiring for T-1384's `own_obligations_clean` guard:
    whether `ticket`'s OWN diff (every file `working_diff(root, "main")`
    reports a hunk in) leaves outstanding (a) a new-symbol `frob:doc` edge
    (COV001), (b) a testsuite strata declaration (SELFAUDIT001), or (c) an
    unapplied REL001 version bump -- the T-1377/T-1379/T-1381 residue
    class: closed clean, then surprised the very next unscoped `frob
    check` with exactly this obligation, because nothing computed it at
    close time.

    REL001 reuses `_required_release_bump` (T-0338's existing read-only
    bump computation, the SAME one `frob ticket land` applies) directly --
    no duplicated version-diffing logic. COV001/SELFAUDIT001 have no
    diff-scoped `--ticket` filter of their own (T-1351: `--ticket` only
    scopes SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT, every other gate
    family's count is repo-wide) -- one `frob check --only gates` run
    supplies the repo-wide `(rule, file)` identity set, filtered here to
    files `ticket`'s own diff touched. This is a deliberate scoping
    choice, not a full new-symbol-only diff parse: a touched file
    carrying a PRE-EXISTING COV001/SELFAUDIT001 finding this ticket did
    not itself introduce also counts against it -- stricter than "only
    symbols this ticket newly added", never looser, since the remedy (add
    the missing edge/declaration) is the same either way for a file the
    ticket is already touching.

    Returns `None` (skip) if `working_diff` itself is unavailable (not a
    git checkout, no merge-base against `main`) or reports no touched
    files at all -- "cannot verify" degrades to a no-op here rather than
    fail-closed, matching `_close_mutation_evidence_for_ticket`'s posture
    for the identical failure mode (additive to the pre-existing evidence
    gates, not the sole gate). Returns `False` (fail-closed) if the `--only
    gates` spawn itself is refused/unparsable, or if any of the three
    obligations is outstanding."""
    from frob.gitio import working_diff

    diff = working_diff(root, "main")
    if diff.is_err:
        _log.warning(
            "ticket close: %s working_diff unavailable (%s), skipping "
            "T-1384 own-obligations check",
            ticket.id,
            diff.danger_err,
        )
        return None
    touched = {h.file for h in diff.danger_ok.hunks}
    if not touched:
        return None

    from frob.app import ticket_runner as _ticket_runner

    rel_result = _ticket_runner._required_release_bump(root, ticket.id)
    rel_dirty = False
    if rel_result.is_err:
        _log.warning(
            "ticket close: %s could not compute the REL001 bump (%s) -- "
            "treating it as an outstanding own-obligation",
            ticket.id,
            rel_result.danger_err,
        )
        rel_dirty = True
    elif rel_result.danger_ok is not None:
        _log.warning(
            "ticket close: %s REL001 version bump outstanding (needs %s)",
            ticket.id,
            rel_result.danger_ok,
        )
        rel_dirty = True

    spawned = _ticket_runner.guarded_subprocess_run(
        [
            _ticket_runner._python_for_tree(root),
            "-m",
            "frob",
            "check",
            "--only",
            "gates",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if spawned.is_err:
        _log.warning(
            "ticket close: %s `frob check --only gates` refused to spawn "
            "(%s) -- cannot verify T-1384 own-obligations, refusing to "
            "close on unverifiable evidence",
            ticket.id,
            spawned.danger_err,
        )
        return False
    proc = spawned.danger_ok
    findings = _ticket_runner._parse_error_findings_from_stdout(
        ticket.id, proc.stdout, proc.returncode
    )
    if findings is None:
        _log.warning(
            "ticket close: %s `frob check --only gates` output had no "
            "parsable gate-summary line -- cannot verify T-1384 "
            "own-obligations, refusing to close on unverifiable evidence",
            ticket.id,
        )
        return False

    obligation_rules = {"COV001", "SELFAUDIT001"}
    dirty = sorted(
        f"{r}:{f}" for r, f in findings if r in obligation_rules and f in touched
    )
    if dirty:
        _log.warning(
            "ticket close: %s own-diff obligation(s) outstanding: %s",
            ticket.id,
            dirty,
        )
    return not (rel_dirty or dirty)


# frob:ticket T-0417
# frob:waive DUP001 reason="T-1089 split moved this function to a new file path with \
# an unchanged body, which the diff-scoped DUP001 gate reads as newly-introduced code \
# and compares against the rest of the tree; the 95% r2 match against \
# frob.tickets._land._reverify_test_count_claim is same-shape (a bool|None-returning \
# re-verify-then-log-and-report helper) but different-domain -- this one re-runs \
# close's own recorded evidence ids against the current tree, that one compares a \
# captured test/evidence count claim for regression at land time; no shared logic to \
# extract, pre-existing structural similarity the split did not create"
def _reverify_evidence_for_close(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """N-02 CLI wiring: whether `ticket`'s own non-cmd evidence ids STILL
    pass when actually re-run against the CURRENT tree at `frob ticket
    close` time -- closing a ticket must never trust the pass observation
    made once, back when `frob ticket evidence` first recorded it (round-2
    audit finding N-02, docs/audits/tickets-testing-round2.md): the tree
    can change arbitrarily between `evidence` and `close`, and until this
    fix `close` (unlike `land`, which already re-verifies post-merge via
    `_reverify_evidence_post_merge`, D-05) never re-ran anything -- a test
    recorded green then later broken by an edit to the source or the test
    itself still closed the ticket.

    Returns `None` (skip the check) when the ticket carries no non-cmd
    evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest channel
    (`add_cmd_evidence`) and nothing here to re-run. Returns `False`
    (fail-closed, blocking the close) if collection itself fails --
    "cannot verify" must never silently become "verified", the same
    posture `_covers_scope_for_ticket` already takes for an unloadable
    graph."""
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd:
        return None

    from frob.app import ticket_runner as _ticket_runner

    collected = _ticket_runner._collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.warning(
            "ticket close: %s evidence collection failed (%s), cannot "
            "re-verify N-02 pass state -- refusing to close on "
            "unverifiable evidence",
            ticket.id,
            collected.danger_err,
        )
        return False
    python_ids, rust_ids, runners = collected.danger_ok
    from frob.app import ticket_runner as _ticket_runner

    passing = _ticket_runner._verify_ids_passing(
        root, non_cmd, python_ids, rust_ids, runners
    )
    failing = [e for e in non_cmd if e not in passing]
    if failing:
        _log.warning(
            "ticket close: %s evidence no longer passes when re-run: %s",
            ticket.id,
            failing,
        )
        return False
    return True


# frob:ticket T-0571
# frob:waive ARCH103 reason="T-0977: best-effort git-rev-parse wrapper -- runs the \
# subprocess, formats the debug log line on failure, returns None; the \
# format-on-failure step is the SAME best-effort-git concern the docstring names, not \
# a distinct one worth splitting out"
def _current_commit(root: Path) -> str | None:
    """Best-effort `git rev-parse HEAD` under `root` (`None` on any git
    failure) -- shared by `_review`'s default `--commit` and `_close`'s
    strict-mode gate so both name the SAME notion of "current commit"."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# frob:ticket T-0571
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_writes_review_record
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_requires_all_flags
def _review(root: Path, cfg: AppConfig) -> None:
    """`frob ticket review <id> --verdict approve|reject --reviewer NAME
    --findings-file PATH [--commit SHA]`: resolve the findings text and
    commit, then call `frob.tickets.record_review` -- the structured,
    first-class adversarial-review evidence channel (T-0571). `--commit`
    defaults to the current `HEAD` under `root` when omitted."""
    from frob.tickets import ReviewVerdict, record_review

    if (
        cfg.ticket_id is None
        or cfg.ticket_review_verdict is None
        or cfg.ticket_reviewer is None
        or cfg.ticket_findings_file is None
    ):
        _log.error(
            "frob ticket review requires <id> --verdict approve|reject "
            "--reviewer NAME --findings-file PATH"
        )
        sys.exit(1)

    try:
        findings = cfg.ticket_findings_file.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "review: could not read --findings-file %s: %s",
            cfg.ticket_findings_file,
            exc,
        )
        sys.exit(1)

    from frob.app import ticket_runner as _ticket_runner

    commit = cfg.ticket_review_commit or _ticket_runner._current_commit(root)
    if commit is None:
        _log.error(
            "review: could not resolve --commit and no --commit was given "
            "(is %s a git checkout?)",
            root,
        )
        sys.exit(1)

    result = record_review(
        root,
        cfg.ticket_id,
        verdict=ReviewVerdict(cfg.ticket_review_verdict),
        reviewer=cfg.ticket_reviewer,
        findings=findings,
        commit=commit,
    )
    if result.is_err:
        _log.error("review failed: %s", result.danger_err)
        sys.exit(1)
    _log.info(
        "%s: recorded review verdict=%s reviewer=%s commit=%s",
        cfg.ticket_id,
        cfg.ticket_review_verdict,
        cfg.ticket_reviewer,
        commit,
    )


# frob:ticket T-0571
def _covers_review_for_ticket(root: Path, cfg: AppConfig, ticket) -> bool | None:  # noqa: ANN001
    """T-0571's CLI-side strict-mode predicate: `None` (skip the check)
    unless BOTH `--strict` was passed on this `close` invocation AND
    `[tickets] require_review_for_close` is true in `frob.toml` -- either
    condition missing means "not opted in", never a silent enforcement.
    When both are true, resolves the current commit and asks
    `frob.tickets.has_approved_review_for_commit`."""
    from frob.tickets import (
        has_approved_review_for_commit,
        load_require_review_for_close,
    )

    if not cfg.ticket_close_strict or not load_require_review_for_close(root):
        return None
    from frob.app import ticket_runner as _ticket_runner

    commit = _ticket_runner._current_commit(root)
    if commit is None:
        _log.warning(
            "ticket close --strict: could not resolve current commit under "
            "%s -- refusing to close on unverifiable review",
            root,
        )
        return False
    return has_approved_review_for_commit(ticket, commit)


# frob:ticket T-0976
def _apply_close_time_evidence(root: Path, cfg: AppConfig) -> None:
    """Apply `frob ticket close`'s optional `--evidence`/`--evidence-cmd`/
    `--skip-mutation-evidence` flags before the close transition itself
    runs: validates and appends any evidence given (exiting on failure so
    a bad flag can never close on unvalidated evidence) and logs the
    justification-required warning for the mutation-evidence escape
    hatch. Caller (`_close`) has already verified `cfg.ticket_id is not
    None` before calling this."""
    assert cfg.ticket_id is not None
    if cfg.ticket_evidence_ids:
        added = _apply_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_ids, cfg.ticket_accepts
        )
        if added.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_added = _apply_cmd_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_cmd, cfg.ticket_accepts
        )
        if cmd_added.is_err:
            sys.exit(1)

    if cfg.ticket_close_skip_mutation_evidence:
        _log.warning(
            "ticket close: %s --skip-mutation-evidence set -- a TEST016 "
            "confirmatory-only-evidence finding will be logged but will NOT "
            "refuse this close (justification required: use only for a "
            "genuine false positive)",
            cfg.ticket_id,
        )


# frob:ticket T-0976
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_true_mutation_evidence_with_skip_flag_is_never_downgraded  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_false_mutation_evidence_without_skip_flag_stays_false  # noqa: E501
def _close_guards_for_ticket(root: Path, cfg: AppConfig, fresh_ticket) -> tuple:  # noqa: ANN001
    """Compute the six independent close-time guard values `transition`
    needs for `frob ticket close`'s strict default (T-0398 covers_scope,
    T-0571 config-gated review, T-0844 mutation evidence, T-0417 N-02
    post-merge re-verify, T-1410 gate-claim verification, T-1387
    own-obligations) -- each guard is its own existing helper; this just
    threads `cfg.ticket_close_skip_mutation_evidence` through to downgrade
    a `False` mutation-evidence verdict to `None` (skip) when the escape
    hatch was passed."""
    from frob.app import ticket_runner as _ticket_runner

    covers_scope = _ticket_runner._covers_scope_for_ticket(root, fresh_ticket)
    from frob.app import ticket_runner as _ticket_runner

    reviewed = _ticket_runner._covers_review_for_ticket(root, cfg, fresh_ticket)
    from frob.app import ticket_runner as _ticket_runner

    mutation_evidence = _ticket_runner._close_mutation_evidence_for_ticket(
        root, fresh_ticket
    )
    if mutation_evidence is False and cfg.ticket_close_skip_mutation_evidence:
        mutation_evidence = None
    from frob.app import ticket_runner as _ticket_runner

    evidence_reverified = _ticket_runner._reverify_evidence_for_close(
        root, fresh_ticket
    )
    from frob.app import ticket_runner as _ticket_runner

    gate_claims_verified = _ticket_runner._close_gate_claims_for_ticket(
        root, fresh_ticket
    )
    from frob.app import ticket_runner as _ticket_runner

    own_obligations_clean = _ticket_runner._close_own_obligations_for_ticket(
        root, fresh_ticket
    )
    return (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    )


# frob:ticket T-0106
# frob:ticket T-0215
# frob:ticket T-0398
# frob:ticket T-0571
def _close(root: Path, cfg: AppConfig) -> None:
    """Transition a ticket to done; if `--evidence` ids or `--evidence-cmd`
    were given, validate and append them first (`_apply_evidence` /
    `_apply_cmd_evidence`) and refuse to transition at all if either is
    unresolvable/fails, so a bad flag can never close a ticket on
    unvalidated evidence. A failed transition is reported through
    `_close_failure_hint` so the operator gets a concrete next command, not
    just the bare state-machine error (T-0215).

    T-0398: this is the CLI's STRICT default -- `covers_scope` is always
    computed (`_covers_scope_for_ticket`) and always passed to
    `transition`, so evidence that covers none of the ticket's touched/
    scope symbols rejects the close (`EvidenceScopeUnbound`) through the
    real `frob ticket close` command.

    T-0571: `reviewed` is only ever non-`None` when BOTH `--strict` was
    passed AND `[tickets] require_review_for_close` is true in
    `frob.toml` (`_covers_review_for_ticket`) -- config-gated, off by
    default, so this never breaks a repo/workflow that has not opted in.

    T-0844: `mutation_evidence` is ALWAYS computed
    (`_close_mutation_evidence_for_ticket`) and passed to `transition`, so
    a security/bug-kind ticket with an ERROR-severity TEST016
    confirmatory-only-evidence finding refuses the direct close the same
    way it already refuses `frob ticket land` -- unless `--skip-mutation-
    evidence` was passed, the close-path twin of land's own escape hatch.

    T-0417 N-02: `evidence_reverified` is ALWAYS computed
    (`_reverify_evidence_for_close`) and passed to `transition`, so a
    ticket whose recorded evidence passed once but no longer passes
    against the CURRENT tree refuses to close -- the direct-close twin of
    `land`'s own post-merge re-verify (D-05), closing the TOCTOU gap where
    `close` (unlike `land`) never re-ran anything.

    T-1410: `gate_claims_verified` is ALWAYS computed
    (`_close_gate_claims_for_ticket`) and passed to `transition`, so a
    ticket carrying an acceptance criterion shaped "0 <RULE> findings
    under <glob>" refuses to close while a live `frob check --only gates`
    run still reports findings for that rule under that glob -- the T-1276
    defect (closed done, LAND-PROOF verified, against 116 live TEST005
    findings under its own criterion's glob) is now refused at the real
    close path, not just in the T-1399 guard's own unit tests."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")
    _apply_close_time_evidence(root, cfg)

    # Re-load: evidence may have just changed above, and covers_scope must
    # be computed against the ticket's CURRENT evidence, not the state
    # loaded before this call's own --evidence/--evidence-cmd applied.
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")
    (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    ) = _close_guards_for_ticket(root, cfg, fresh_ticket)

    result = transition(
        root,
        cfg.ticket_id,
        TicketState.DONE,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        gate_claims_verified=gate_claims_verified,
        own_obligations_clean=own_obligations_clean,
    )
    if result.is_err:
        _log.error(_close_failure_hint(cfg.ticket_id, ticket.state, result.danger_err))
        sys.exit(1)
    _log.info("%s closed (done)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="done")

    # frob:ticket T-1178
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): close {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-1005
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_reruns_verification_and_refreshes_recap_state_unchanged  # noqa: E501
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_surfaces_now_failing_evidence_loudly  # noqa: E501
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_refuses_non_done_ticket
def _reverify(root: Path, cfg: AppConfig) -> None:
    """`frob ticket reverify <id>`: the missing verb for a post-close
    send-back (churn item 6, docs/audits/coordination-churn.md -- ~5
    observed occurrences). After a done ticket gets a TEST016-driven
    evidence strengthening (or any other scope/evidence/done-report edit
    applied post-close), nothing could previously re-run close's own
    verification suite against it: `close` itself refuses a done->done
    transition, and `start`/`sweep` both refuse a done ticket outright --
    so a land had to proceed on trust in the ORIGINAL close-time recap
    alone, even though the ticket's evidence/scope may have changed since.

    Re-runs the exact same five close-time guards `_close` computes
    (`_close_guards_for_ticket` -- D-02 covers_scope, T-0571 reviewed,
    T-0844 mutation_evidence, T-0417 evidence_reverified, T-1410
    gate_claims_verified, all shared, no duplicated computation) and the
    exact same state-machine verification
    `transition(..., TicketState.DONE, ...)` runs at close time
    (`frob.tickets.reverify_close_guard`, which wraps the SAME
    `_done_transition_guard` -- structural + T-0854 live-tracker-citation
    + T-0756 new-gate-rule-acceptance too), against the ALREADY-done
    ticket -- but NEVER calls `transition`, so no write, no state change,
    either way. `--evidence`/`--evidence-cmd`/`--accepts`/`--strict`/
    `--skip-mutation-evidence` behave identically to `close`'s own flags
    (`_apply_close_time_evidence`, shared).

    A failing guard exits 1 loudly via the SAME `_close_failure_hint`
    remedy text `close` itself would show (now under the `"reverify"`
    verb) and leaves the recap untouched -- this is the "surfaces a
    now-failing evidence id loudly" half of the contract. A fully passing
    reverify refreshes the recap: `frob.tickets.recover_done_report_why`
    recovers the ticket's existing Done-report narrative verbatim (the
    mechanical inverse of `compose_done_report`'s own narrative half, so
    the operator never retypes it), and a fresh `set_done_report` call
    (same T-0754 claims-capture callables `_done_report` already supplies)
    rewrites Changed/Evidence/Captured-claims against the CURRENT tree --
    the "refreshes the recap" half."""
    from frob.tickets import TicketState, recover_done_report_why, reverify_close_guard
    from frob.tickets import set_done_report as _set_done_report

    if cfg.ticket_id is None:
        _log.error("frob ticket reverify requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="reverify")
    if ticket.state is not TicketState.DONE:
        _log.error(
            "reverify failed: %s is %s, not done -- reverify re-checks an "
            "already-closed ticket, it does not close one (use `frob "
            "ticket close %s` instead)",
            cfg.ticket_id,
            ticket.state.value,
            cfg.ticket_id,
        )
        sys.exit(1)

    _apply_close_time_evidence(root, cfg)

    # Re-load: --evidence/--evidence-cmd may have just changed the ticket's
    # recorded evidence, and every guard below must see the CURRENT
    # evidence, not the state loaded before those flags applied (mirrors
    # `_close`'s own re-load-after-apply sequencing exactly).
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="reverify")
    (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    ) = _close_guards_for_ticket(root, cfg, fresh_ticket)

    guard_result = reverify_close_guard(
        root,
        cfg.ticket_id,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        gate_claims_verified=gate_claims_verified,
        own_obligations_clean=own_obligations_clean,
    )
    if guard_result.is_err:
        _log.error(
            _close_failure_hint(
                cfg.ticket_id,
                fresh_ticket.state,
                guard_result.danger_err,
                verb="reverify",
            )
        )
        sys.exit(1)

    why = recover_done_report_why(fresh_ticket.body)
    if why is None:
        _log.error(
            "reverify failed: %s verification passed but no recoverable "
            "Done-report narrative was found to replay -- recap NOT "
            "refreshed (state remains done, unchanged); this can only "
            "happen for a Done report predating T-0458's auto-fill "
            "sections -- run `frob ticket done-report %s --why TEXT` once "
            "to give it one, then retry `frob ticket reverify %s`",
            cfg.ticket_id,
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    _shared_spawn = _shared_check_spawn_fn(root, cfg.ticket_id)
    report_result = _set_done_report(
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
    if report_result.is_err:
        _log.error(
            "reverify: %s verification passed but the recap refresh "
            "failed (%s) -- state remains done, unchanged",
            cfg.ticket_id,
            report_result.danger_err,
        )
        sys.exit(1)
    _log.info(
        "%s reverified: full close-time verification suite passed, recap "
        "refreshed, state unchanged (done)",
        cfg.ticket_id,
    )


# frob:ticket T-1162
def _load_ticket_for_fail(root: Path, ticket_id: str):
    """T-1162: pure I/O -- load the queue and return the named ticket, or
    `sys.exit(1)` (with a logged reason) on a load error or unknown id.
    Extracted from `_fail` to isolate its I/O from the decision/formatting
    steps that follow."""
    from frob.tickets import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("fail failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.error("no ticket %s", ticket_id)
        sys.exit(1)
    return ticket


# frob:ticket T-1162
def _record_fail_entry(root: Path, ticket_id: str, ticket, summary: str) -> None:
    """T-1162: pure I/O -- append a `FailureEntry` (attempt number derived
    from the ticket's existing body) via `record_failure`, or `sys.exit(1)`
    on error. Extracted from `_fail`."""
    from frob.tickets import FailureEntry, record_failure

    attempt = ticket.body.count("attempt ") + 1
    entry = FailureEntry(date=date.today(), attempt=attempt, summary=summary)
    result = record_failure(root, ticket_id, entry)
    if result.is_err:
        _log.error("fail failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s: recorded failure attempt %d", ticket_id, attempt)


# frob:ticket T-1162
def _requeue_if_in_progress(root: Path, ticket_id: str, ticket) -> None:
    """T-1162: decision (was the ticket IN_PROGRESS?) plus the I/O that
    follows it -- requeue (IN_PROGRESS -> QUEUED) to release the
    cross-worktree lease, per the T-1131 incident documented on `_fail`.
    A ticket not IN_PROGRESS is left unchanged, matching pre-T-1131
    behavior for that case."""
    from frob.tickets import TicketState, transition

    if ticket.state is not TicketState.IN_PROGRESS:
        return
    requeued = transition(root, ticket_id, TicketState.QUEUED)
    if requeued.is_err:
        _log.error(
            "fail: %s failure log recorded but requeue failed (%s) -- "
            "lease NOT released, needs manual attention",
            ticket_id,
            requeued.danger_err,
        )
        sys.exit(1)
    _log.info("%s: requeued (in-progress -> queued), lease released", ticket_id)


# frob:ticket T-1131
# frob:ticket T-1130
# frob:ticket T-1162
def _fail(root: Path, cfg: AppConfig) -> None:
    """`frob ticket fail <id> --summary TEXT`: record a dead-end failure
    log entry, then requeue the ticket (T-1131).

    T-1131 (the T-1050 incident): `record_failure` only ever appended the
    failure-log entry -- it never called `transition`, so a ticket that
    was IN_PROGRESS when fail-logged stayed IN_PROGRESS forever, holding
    its cross-worktree lease (`_sync_cross_worktree_lease` only releases a
    lease on a `transition` call OUT of IN_PROGRESS, and `record_failure`
    never made one). An agent fail-logged a superseded ticket, removed its
    worktree, and the ticket sat in-progress pointing at a now-nonexistent
    path until a coordinator noticed and hand-dropped it. Requeuing
    (IN_PROGRESS -> QUEUED, a legal `_TRANSITIONS` edge) after a fail-log
    is the correct semantics anyway: a failed attempt is a retry
    candidate, not a permanently stuck ticket -- and it is the one
    `transition` call that actually releases the lease. A ticket that was
    NOT IN_PROGRESS when fail-logged (no lease to release) is left in its
    current state unchanged, matching pre-T-1131 behavior for that case.

    T-1130: auto-commits the fail-log (plus any requeue transition) as ONE
    ledger change, the same way `start` auto-commits its own transition
    (T-1054 parity) -- `--no-commit` (`cfg.ticket_no_commit`) opts out.

    T-1162 split this into `_load_ticket_for_fail` (I/O),
    `_record_fail_entry` (I/O), and `_requeue_if_in_progress`
    (decision+I/O) -- this function is now their composition plus the
    final ledger commit."""
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_id is None or cfg.ticket_summary is None:
        _log.error("frob ticket fail requires <id> and --summary")
        sys.exit(1)

    ticket = _load_ticket_for_fail(root, cfg.ticket_id)
    _record_fail_entry(root, cfg.ticket_id, ticket, cfg.ticket_summary)
    _requeue_if_in_progress(root, cfg.ticket_id, ticket)

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): {cfg.ticket_id} fail-logged",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-0579
# frob:ticket T-1130
def _drop(root: Path, cfg: AppConfig) -> None:
    """CLI wiring for `frob ticket drop <id> --reason TEXT [--absorbed-by
    T-####]` (T-0579): the first-class replacement for hand-editing
    `state: dropped` directly. Delegates entirely to `frob.tickets.
    drop_ticket` for the reason-line + transition + lease-release
    mechanics; this layer only validates required args and reports the
    Result.

    T-1130: auto-commits the drop's ledger change (reason line + DROPPED
    transition) the same way `start` auto-commits its own transition
    (T-1054 parity) -- `--no-commit` (`cfg.ticket_no_commit`) opts out."""
    from frob.tickets import drop_ticket
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket drop requires <id> and --reason")
        sys.exit(1)

    result = drop_ticket(
        root, cfg.ticket_id, cfg.ticket_reason, absorbed_by=cfg.ticket_absorbed_by
    )
    if result.is_err:
        _log.error("drop failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s dropped", cfg.ticket_id)

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): drop {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-0094
# frob:ticket T-0106
# frob:ticket T-0215
