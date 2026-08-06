"""frob.gates._fix_engine_sync -- Tier-A derived-artifact-sync auto-fix handlers.

Sibling of the `frob.gates._fix_engine_text` split (T-1646, LARGE001
residue burndown): `_fix_engine_text` keeps the LINE-scoped handlers
(FMT001, SUPPRESS001, E501) that resolve a fix by rewriting the ONE
source line a `Violation` already names; every handler in THIS module
instead resolves its fix by SYNCING one generated/derived artifact back
to its source of truth -- REG010/REL002 (registry <-> gate-rule-id and
release notes sync), SYS104/SYS100 (`.strata` text rewrites via the same
writers `frob sys sync-interface` already uses), COV002 (insert a
`frob:ticket` directive above an unbound symbol), and WAIVE004 (remove a
waiver already proven dead by a fresh gate run). `TIER_A_HANDLERS` in
`_fix_engine` imports every public `fix_*` symbol from both this module
and `_fix_engine_text` and dispatches through the same uniform `(root,
snapshot, queue, ticket_id) -> list[FixApplied]` call shape every handler
uses -- this split changes no behavior, only which file a given handler's
body lives in.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool carried forward at the \
# T-1646 LARGE001 split: this module's exclusivity-vocabulary hits are the same \
# source-level design-rationale prose (docstrings/comments describing already- \
# implemented internal behavior, verifiable by reading the code they annotate) that \
# src/frob/gates/_fix_engine.py's own module-level INV006 waiver already covers -- \
# moved verbatim with the code, not a new claim"

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._fix_engine_shared import FixApplied, _write_text
from frob.graph import GraphSnapshot
from frob.tickets import TicketQueue

if TYPE_CHECKING:
    from frob.gates import GateReport

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REG010 (T-1261): a live gate rule id with no `CHK-GATE-<rule>` entry in
# check-coverage.yaml -- `frob registry audit --sync-gate-rules` names
# itself as its own remedy.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_reg010_registry_sync(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1261): REG010 already names its own remedy verbatim
    (`frob registry audit --sync-gate-rules`) -- calls `sync_gate_rule_
    entries` (`frob.registry._staleness`, the exact function that command
    already wraps) directly against `docs/design/registry/check-
    coverage.yaml`, filing one `CHK-GATE-<rule>` entry per live gate rule
    the registry is missing one for. Idempotent: a rule already covered
    is silently skipped, never duplicated (`missing_gate_rule_ids` is
    recomputed fresh every call). REG008 (an entry claiming `handled_by:`
    a rule with no matching `frob:enforces` edge in CODE) is a different,
    genuinely Tier-C shape -- which rule's code should carry that
    directive is a judgment call this handler does not guess at, so only
    REG010 is wired here."""
    from frob.registry._staleness import sync_gate_rule_entries

    del snapshot  # signature uniformity only, this handler reads the yaml itself
    registry_path = root / "docs" / "design" / "registry" / "check-coverage.yaml"
    if not registry_path.is_file():
        return []
    from frob.gates._waive import known_gate_rule_ids

    result = sync_gate_rule_entries(registry_path, known_gate_rule_ids())
    if result.is_err or not result.danger_ok:
        return []
    added = result.danger_ok
    rel = registry_path.relative_to(root).as_posix()
    return [
        FixApplied(
            rule="REG010",
            file=rel,
            line=0,
            detail=f"filed CHK-GATE-<rule> entries for: {', '.join(added)}",
        )
    ]


# ---------------------------------------------------------------------------
# REL002 (T-1261): a derived release artifact disagrees with `.frob-
# release.json`'s authoritative version -- `frob release sync` names
# itself as its own remedy.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_rel002_release_sync(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1261): REL002 already names its own remedy verbatim
    (`frob release sync`) -- regenerates `pyproject.toml`'s version,
    `uv.lock`, and CHANGELOG.md's skeleton entry FROM `.frob-release.
    json` (the ONE version authority), reusing the exact `frob.release`
    functions `frob release sync`'s own CLI dispatches to
    (`authoritative_version`/`rewrite_pyproject_version`/
    `changelog_skeleton_entry`, plus `uv lock` via `frob.gitio.run_argv`).
    Never writes `.frob-release.json` itself, only the three derived
    artifacts -- T-1137's anti-goal that no handler treats the manifest
    (or `frob.toml`/ratchet state) as a target it may write."""
    from frob.gitio import run_argv
    from frob.release import (
        authoritative_version,
        changelog_skeleton_entry,
        rewrite_pyproject_version,
    )

    del snapshot  # signature uniformity only, this handler reads the manifest itself
    version_result = authoritative_version(root)
    if version_result.is_err:
        return []
    version = version_result.danger_ok

    applied: list[FixApplied] = []
    rewritten = rewrite_pyproject_version(root, version)
    if rewritten.is_ok and rewritten.danger_ok:
        applied.append(
            FixApplied(
                rule="REL002",
                file="pyproject.toml",
                line=0,
                detail=f"version -> {version}",
            )
        )

    if (root / "pyproject.toml").exists() and (root / "uv.lock").exists():
        locked = run_argv(["uv", "lock"], cwd=root, timeout_s=120.0)
        if locked.is_ok and locked.danger_ok.returncode == 0:
            applied.append(
                FixApplied(
                    rule="REL002", file="uv.lock", line=0, detail=f"synced to {version}"
                )
            )

    if changelog_skeleton_entry(root, version):
        applied.append(
            FixApplied(
                rule="REL002",
                file="CHANGELOG.md",
                line=0,
                detail=f"added skeleton entry for {version}",
            )
        )
    return applied


# ---------------------------------------------------------------------------
# SYS104 (T-1531): a node's declared `interface=[...]` surface drifted from
# its real bound-code public surface -- `frob sys sync-interface` (T-1150)
# already names its own remedy verbatim; this handler wires that existing
# writer into the generic Tier-A table so both sweep paths (the pre-land
# absorption step already calls it separately, `_sync_interface_pre_land_
# step`, but the POST-land unscoped sweep never did) get the same fix.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys104_interface_union_applies_via_apply_tier_a_fixes  # noqa: E501
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys104_no_design_dir_is_a_no_op  # noqa: E501
# frob:ticket T-1531
def fix_sys104_interface_union(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1531): SYS104 already names its own remedy verbatim
    (`frob sys sync-interface`) -- reuses `sync_interface_report`/
    `apply_sync_interface` (`frob.strata._sync_interface`, T-1150)
    directly, the exact functions that CLI verb itself calls, so no
    detection logic is duplicated here. A design root that does not
    resolve (no `design/` dir, a parse/elaborate failure) is logged and
    treated as no fixes applied, matching every other handler's
    best-effort posture."""
    from frob.strata._sync_interface import apply_sync_interface, sync_interface_report

    del snapshot  # signature uniformity only, this handler reads the design tree itself
    if not (root / "design").is_dir():
        return []
    report = sync_interface_report(root, "design")
    if report.is_err:
        _log.warning(
            "tier-a fixes: SYS104 sync-interface skipped: %s", report.danger_err
        )
        return []
    result = report.danger_ok
    if not result.has_drift:
        return []
    written = apply_sync_interface(root, result)
    applied: list[FixApplied] = []
    for file_result in result.files:
        if file_result.path not in written:
            continue
        for diff in file_result.diffs:
            detail_bits = []
            if diff.added:
                detail_bits.append(f"+{','.join(diff.added)}")
            if diff.removed:
                detail_bits.append(f"-{','.join(diff.removed)}")
            applied.append(
                FixApplied(
                    rule="SYS104",
                    file=file_result.path,
                    line=0,
                    detail=f"node {diff.node} interface= {' '.join(detail_bits)}",
                )
            )
    return applied


# ---------------------------------------------------------------------------
# SYS100 core (T-1531): a net/fs-write/exec effect observed in a file with
# no `may "<kind>" via [...]` grant covering it -- widen (or create) the
# grant's `via` list to include the observed file, sorted union, via the
# `frob.strata._sync_may` writer (module docstring there: SYS100's
# EXTENDED case, eval/process-control/ffi/..., has no per-file evidence to
# add and is deliberately NOT handled here).
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys100_may_via_union_applies_via_apply_tier_a_fixes  # noqa: E501
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys100_no_design_dir_is_a_no_op  # noqa: E501
# frob:ticket T-1531
def fix_sys100_may_via_union(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1531): widen a node's `may "<kind>" via [...]` grant
    (or insert a brand-new via-scoped grant) to cover a file
    `check_capability_conformance` (SYS100 core) observed exercising an
    already-granted capability kind outside its declared `via` surface --
    `frob.strata._sync_may.sync_may_report`/`apply_sync_may`, this
    handler's own writer (T-1531, module docstring there for the scope
    cut: SYS100 EXTENDED is not handled). A design root that does not
    resolve is logged and treated as no fixes applied."""
    from frob.strata._sync_may import apply_sync_may, sync_may_report

    del snapshot  # signature uniformity only, this handler reads the design tree itself
    if not (root / "design").is_dir():
        return []
    report = sync_may_report(root, "design")
    if report.is_err:
        _log.warning("tier-a fixes: SYS100 sync-may skipped: %s", report.danger_err)
        return []
    result = report.danger_ok
    if not result.has_drift:
        return []
    written = apply_sync_may(root, result)
    applied: list[FixApplied] = []
    for file_result in result.files:
        if file_result.path not in written:
            continue
        for diff in file_result.diffs:
            verb = "created" if diff.created else "widened"
            applied.append(
                FixApplied(
                    rule="SYS100",
                    file=file_result.path,
                    line=0,
                    detail=(
                        f"node {diff.node} may {diff.kind!r} via {verb} "
                        f"+{','.join(diff.added_files)}"
                    ),
                )
            )
    return applied


# COV002 (T-1548): a changed symbol with no `frob:ticket` edge to an open
# ticket AND no covering ticket scope -- insert `# frob:ticket
# <landing-id>` above the symbol, but ONLY when the caller identifies a
# real landing ticket id and that finding is against the CURRENT working
# diff (this land's own diff, never a guess at some other ticket's
# unrelated change).
# ---------------------------------------------------------------------------


# frob:tests \
# tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_stra\
# ta_file_gets_slash_slash_leader
# frob:tests \
# tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_rust\
# _file_gets_slash_slash_leader
# frob:tests \
# tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_pyth\
# on_file_gets_hash_leader
# frob:tests \
# tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader.test_unkn\
# own_extension_refuses_insertion
# frob:ticket T-1581
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to marker_for, a \
# cross-module helper the resolver cannot see through; the one real raise path (file \
# read) is caught below"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for lines[-1], a list index guarded by an \
# immediately-preceding 'if lines and ...' emptiness check, so the index is always \
# valid by construction; the resolver's syntactic bracket scan cannot see the guard"
def _insert_ticket_directive_above(
    root: Path, rel_file: str, line: int, ticket_id: str
) -> bool:
    """Insert `# frob:ticket <ticket_id>` (leader resolved per target
    language via `frob.gates._fmt_directives.marker_for` -- `//` for a
    `.rs`/`.strata` source, `#` for `.py`, etc.) as the new physical line
    immediately BEFORE 1-indexed `line` of `root/rel_file` -- the
    directive attaches to the symbol whose definition starts at `line`,
    exactly where every other hand-written `frob:ticket` directive in this
    repo already sits. T-1581: this used to hardcode its own narrower
    suffix table defaulting an unrecognized suffix to `#`, which is what
    let T-1548's own land silently write a Python-style directive into a
    `.strata` file (leader `//`) and break strata parsing on main; it now
    reuses the one shared marker table instead of guessing, and REFUSES
    (returns `False`) for a suffix `marker_for` does not recognize rather
    than defaulting to `#`. Returns `False` (a no-op) on any read/write
    failure, an out-of-range `line`, or an unknown suffix -- never raises,
    matching every other Tier-A handler's "no rewrite is better than a bad
    one" posture."""
    from frob.gates._fmt_directives import marker_for

    path = root / rel_file
    marker = marker_for(rel_file)
    if marker is None:
        _log.warning(
            "COV002 auto-fix: no known comment leader for %r, skipping insertion",
            rel_file,
        )
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = text.splitlines(keepends=True)
    idx = line - 1
    if idx < 0 or idx > len(lines):
        return False
    newline = "\n"
    if lines and not lines[-1].endswith("\n"):
        newline = "\n"  # last-line-no-trailing-newline files still get one
    directive_line = f"{marker} frob:ticket {ticket_id}{newline}"
    lines.insert(idx, directive_line)
    return _write_text(path, "".join(lines))


# frob:doc docs/modules/gates.md#fix_cov002_ticket_directive_insertion-auto-fix-t-1548  # noqa: E501
# frob:tests tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion.test_open_landing_ticket_gets_directive_inserted_and_reverifies_clean  # noqa: E501
# frob:tests tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion.test_no_ticket_id_is_a_no_op  # noqa: E501
# frob:ticket T-1548
def fix_cov002_ticket_directive_insertion(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    ticket_id: str | None,
) -> list[FixApplied]:
    """Tier-A fix (T-1548): for every COV002 finding (a changed symbol
    accounted for by neither a direct `frob:ticket` edge nor an open
    ticket's scope) against the CURRENT working diff, insert `# frob:ticket
    <ticket_id>` directly above the symbol -- but only when `ticket_id`
    names a REAL, currently OPEN ticket in `queue` (never guesses at which
    ticket "should" cover an orphaned symbol) and the diff producing the
    finding is this call's own `working_diff(root, "main")` -- i.e. this
    land's own diff, never some other ticket's unrelated change (there is
    no other diff this handler could read `git`-side that would mean
    anything else). A `ticket_id` of `None` (this handler invoked outside
    a landing context, e.g. a bare `frob check --fix`) is a whole-handler
    no-op -- there is no id to cite, and Tier-A never guesses one."""
    if ticket_id is None or ticket_id not in queue.tickets:
        return []
    from frob.gates import _OPEN_STATES, _cov002
    from frob.gitio import working_diff

    if queue.tickets[ticket_id].state not in _OPEN_STATES:
        return []

    diff_result = working_diff(root, "main")
    if diff_result.is_err:
        _log.warning(
            "COV002 auto-fix: working_diff against main failed (%s), skipping",
            diff_result.danger_err,
        )
        return []
    diff = diff_result.danger_ok
    violations = _cov002(snapshot, queue, diff, active_ticket=ticket_id)
    applied: list[FixApplied] = []
    for violation in violations:
        if _insert_ticket_directive_above(
            root, violation.file, violation.line, ticket_id
        ):
            applied.append(
                FixApplied(
                    rule="COV002",
                    file=violation.file,
                    line=violation.line,
                    detail=(
                        f"inserted 'frob:ticket {ticket_id}' above {violation.symref}"
                    ),
                )
            )
    return applied


# ---------------------------------------------------------------------------
# WAIVE004 (T-1261): a `frob:waive` matching zero findings -- ONLY ever
# trustworthy on a genuine full, unscoped run (T-1133's own disclaimer);
# this handler independently manufactures that full run itself rather
# than trusting whatever scope the outer `--fix` invocation used.
# ---------------------------------------------------------------------------

#: A single-physical-line `# frob:waive RULE ...` (or `//` for non-Python
#: sources) comment with NO trailing backslash continuation -- the only
#: shape this handler ever deletes. A multi-line continued waiver (`\` at
#: end of line, T-1134's own carried-waiver precedent) is left alone: Tier
#: A never guesses which of several physical lines to remove from a
#: continued directive.
_WAIVE_SINGLE_LINE_RE = re.compile(r"^\s*(#|//)\s*frob:waive\s+(\S+)\b")

#: T-1323 incident guard: how many WAIVE004 candidates for the SAME target
#: rule in one self-manufactured `run_gates()` call is treated as a mass
#: invalidation signature rather than N independent legitimately-stale
#: waivers. The 2026-07-29 incident stripped 50 files' worth of
#: `frob:waive PERF00x` comments in one `apply_tier_a_fixes` pass because a
#: natives-degraded verification run under-reported PERF findings to zero
#: across the whole tree -- every real PERF waiver looked simultaneously
#: stale. A handful of a rule genuinely going stale together (e.g. a
#: refactor that deletes the pattern a few waivers covered) is plausible;
#: dozens going stale in the SAME run is not -- it is the signature of the
#: verification itself under-reporting, not of the waivers. Chosen well
#: below the incident's own 50-waiver footprint so this guard would have
#: caught it with margin to spare, and well above the handful a normal
#: single-PR cleanup would ever produce for one rule at once.
_WAIVE004_MASS_INVALIDATION_THRESHOLD = 5

#: `GateStats.skipped` names that `_build_ticket_scoped_jobs` (`frob.gates.
#: __init__`) appends ROUTINELY whenever `run_gates` has no bound ticket to
#: enforce `scope`/`prework` against -- true on every genuinely unscoped
#: full run this handler itself ever manufactures (it never passes
#: `ticket=`), so these two are NOT a degradation signal, only a normal
#: consequence of the call shape this handler always uses. Any OTHER
#: skipped stage name is unusual and treated as degraded.
_ROUTINE_UNSCOPED_SKIPS = frozenset({"scope", "prework"})


def _degraded_verification_reason(report: GateReport) -> str | None:
    """The reason `report` (the fresh `run_gates()` call
    `fix_waive004_stale_waiver` manufactures for itself) is NOT trustworthy
    enough to act on, or `None` when it looks like a genuine full run.

    Two structural signals, both already surfaced by `run_gates` itself
    rather than re-derived here: a `NATIVE001` finding means the whole run
    short-circuited to that one honest-root-cause report because a
    declared native extension failed to import (stale/missing natives --
    `_native_unavailable_report`), and a `GateStats.skipped` entry OTHER
    than the routine unscoped-run `scope`/`prework` pair
    (`_ROUTINE_UNSCOPED_SKIPS`) means some other gate stage did not run at
    all. Either makes "this rule had 0 findings" indistinguishable from
    "the gate that would have found something simply didn't run" (T-1133's
    own WAIVE004 caveat, T-1323 extends it to this handler's
    self-manufactured run too)."""
    for violation in report.violations:
        if violation.rule == "NATIVE001":
            return f"native extension unavailable: {violation.message}"
    unexpected_skips = sorted(set(report.stats.skipped) - _ROUTINE_UNSCOPED_SKIPS)
    if unexpected_skips:
        return f"gate stage(s) skipped: {', '.join(unexpected_skips)}"
    return None


def _mass_invalidation_rules(candidates: list[tuple[str, int, str]]) -> dict[str, int]:
    """Every target rule in `candidates` (each a `(file, line, rule)`
    WAIVE004 deletion candidate) whose count meets or exceeds
    `_WAIVE004_MASS_INVALIDATION_THRESHOLD`, mapped to its count -- the
    T-1323 incident's own shape (one rule family's waivers ALL going
    stale in the same run) treated as anomalous-zero-findings evidence in
    its own right, without needing a separately recorded baseline pool to
    compare against. Returns EVERY rule meeting the threshold (not just
    the first), so `_drop_untrustworthy_mass_stale_candidates` can report
    and drop each one by name."""
    counts: dict[str, int] = {}
    for _file, _line, rule in candidates:
        counts[rule] = counts.get(rule, 0) + 1
    return {
        rule: count
        for rule, count in counts.items()
        if count >= _WAIVE004_MASS_INVALIDATION_THRESHOLD
    }


def _is_single_line_waiver(line: str, rule: str) -> bool:
    """True if `line` is a bare, non-continued `frob:waive <rule>` comment
    line -- the one shape `fix_waive004_stale_waiver` ever deletes."""
    if line.rstrip("\n").endswith("\\"):
        return False
    match = _WAIVE_SINGLE_LINE_RE.match(line)
    return match is not None and match.group(2) == rule


def _remove_waiver_line(path: Path, line: int, rule: str) -> bool:
    """Delete 1-indexed `line` of `path` if it is a bare single-line
    `frob:waive <rule>` comment (`_is_single_line_waiver`); a no-op
    (returns `False`) otherwise -- the directive moved, is continued
    across multiple lines, or was already removed by a prior run."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = text.splitlines(keepends=True)
    idx = line - 1
    try:
        if idx < 0 or idx >= len(lines):
            return False
        if not _is_single_line_waiver(lines[idx], rule):
            return False
        del lines[idx]
    except (KeyError, IndexError, TypeError):
        # Same "the directive moved, do nothing" contract as the OSError
        # branch above -- a stale recorded `line` must not crash the
        # whole WAIVE004 auto-fix pass (EXHAUST001/EXHAUST002, T-1371).
        return False
    except Exception:
        return False
    return _write_text(path, "".join(lines))


def _waive004_verified_candidates(
    root: Path, gates: frozenset[str], ticket: str | None
) -> list[tuple[str, int, str]] | None:
    """`fix_waive004_stale_waiver`'s own self-manufactured `run_gates()`
    call, split out to keep the caller under ARCH001's function-length
    ceiling: `None` if the run errored or looked degraded
    (`_degraded_verification_reason`) -- either means "delete nothing at
    all", per this handler's prove-fresh-or-do-nothing contract (T-1323).
    Otherwise the `(file, line, target_rule)` WAIVE004 deletion
    candidates from a verified-trustworthy run, with every rule showing a
    mass-invalidation shape (`_mass_invalidation_rules`) filtered back
    OUT -- see `_drop_untrustworthy_mass_stale_candidates` for why that
    refusal is unconditional again (T-1592)."""
    from frob.gates import GateConfig, run_gates

    result = run_gates(GateConfig(root=str(root), gates=gates, ticket=ticket))
    if result.is_err:
        _log.error(
            "WAIVE004 auto-fix: self-manufactured run_gates() errored (%s) -- "
            "deleting nothing",
            result.danger_err,
        )
        return None

    report = result.danger_ok
    degraded_reason = _degraded_verification_reason(report)
    if degraded_reason is not None:
        _log.error(
            "WAIVE004 auto-fix: self-manufactured verification run looks degraded "
            "(%s) -- deleting nothing",
            degraded_reason,
        )
        return None

    candidates: list[tuple[str, int, str]] = []
    for violation in report.violations:
        if violation.rule != "WAIVE004":
            continue
        target_rule = _waive004_target_rule(violation.message)
        if target_rule is None:
            continue
        candidates.append((violation.file, violation.line, target_rule))

    return _drop_untrustworthy_mass_stale_candidates(candidates)


def _drop_untrustworthy_mass_stale_candidates(
    candidates: list[tuple[str, int, str]],
) -> list[tuple[str, int, str]]:
    """Drop every candidate belonging to a rule `_mass_invalidation_rules`
    flags: one rule's waivers ALL going stale in a single run is the
    signature of a degraded/under-reporting run, not of genuinely dead
    waivers (T-1323, the 2026-07-29 incident).

    T-1592 restores this unconditional refusal. T-1579 had made it
    conditional on `_rule_has_live_finding` -- "one live finding proves
    the detector ran, so mass-staleness is trustworthy" -- which a
    PARTIALLY degraded run defeats: a stale-natives worktree still finds
    some PERF004 lexically while missing every site the waivers actually
    cover. Measured 2026-08-05: the perf gate reported ZERO PERF004 while
    `_degraded_verification_reason` returned None, the escape opened, and
    55 live waivers across arch/strata/perf/graph/vet were deleted during
    a land. The escape can only come back once the degraded-run signal
    fires for a silently under-reporting perf/reach substrate -- which is
    exactly what T-1578 does NOT yet cover."""
    mass_rules = _mass_invalidation_rules(candidates)
    for mass_rule, count in mass_rules.items():
        _log.error(
            "WAIVE004 auto-fix: %d frob:waive %s directives went stale in one "
            "run (>= %d threshold) -- treating as a degraded/under-reporting "
            "run, deleting nothing for this rule",
            count,
            mass_rule,
            _WAIVE004_MASS_INVALIDATION_THRESHOLD,
        )
    if not mass_rules:
        return candidates
    return [c for c in candidates if c[2] not in mass_rules]


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_waive004_stale_waiver(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    *,
    gates: frozenset[str] = frozenset(),
    ticket: str | None = None,
) -> list[FixApplied]:
    """Tier-A fix (T-1261): delete a `frob:waive` directive that matches
    ZERO findings on a genuine full, unscoped run (WAIVE004) -- mirroring
    `frob.gates._waive`'s own "trust this only from a full run" caveat
    (T-1133).

    `gates`/`ticket` mirror `GateConfig`'s own scoping fields; both empty/
    `None` (the default) means "full, unscoped" exactly as `_assemble_
    gate_report`'s `full_unscoped_run = not cfg.gates and cfg.ticket is
    None` already computes it. When either is set, this handler refuses
    to act at all -- a scoped run's "0 findings" is indistinguishable
    from "the gate that would have matched simply did not run this
    time" (T-1133), so acting on it would risk deleting a waiver that is
    still genuinely needed. `apply_tier_a_fixes`/`TIER_A_HANDLERS` always
    call this with the defaults (a full run) -- the keyword params exist
    so this refusal is directly testable without needing to thread CLI
    scope state through the shared 3-arg Tier-A handler signature.

    Independently RE-RUNS the gates suite itself (`run_gates`) rather
    than trusting any violation set the caller may already have computed
    -- the finding this handler acts on is always freshly sourced from a
    genuine full run it manufactured itself, never a stale/ambient one.

    T-1323: prove-fresh-or-do-nothing. Before deleting anything, checks
    that self-manufactured run for a structural degradation signal
    (`_degraded_verification_reason` -- stale/missing natives, any
    skipped gate stage); either one aborts the ENTIRE batch -- zero
    waivers deleted, not a partial subset -- rather than acting on a
    verification run this handler cannot vouch for.

    After collecting candidates, also checks for a mass-invalidation
    shape (`_mass_invalidation_rules` -- one rule's waivers ALL going
    stale together in a single run, the 2026-07-29 incident's own
    signature). T-1579 briefly relaxed this into a per-rule escape keyed on
    the rule having one live finding elsewhere; T-1592 reverted that after
    it deleted 55 live waivers during a land, since a PARTIALLY degraded
    run satisfies the escape. Each flagged rule now has its candidates
    dropped, one rule at a time and logged by name (the
    degraded-run signature `_degraded_verification_reason` targets from
    the other, structural direction). Every other, non-mass-stale rule's
    candidates are never affected by this check either way."""
    del queue  # signature uniformity only, this handler re-runs the gates itself
    if gates or ticket is not None:
        return []

    candidates = _waive004_verified_candidates(root, gates, ticket)
    if candidates is None:
        return []

    applied: list[FixApplied] = []
    for file, line, target_rule in candidates:
        if _remove_waiver_line(root / file, line, target_rule):
            applied.append(
                FixApplied(
                    rule="WAIVE004",
                    file=file,
                    line=line,
                    detail=f"removed stale frob:waive {target_rule} (0 findings this run)",  # noqa: E501
                )
            )
    return applied


#: `_waive004_violations`' own message shape: `"WAIVE004: {src} frob:waive
#: {rule} matches 0 findings..."` -- parsed back out rather than adding a
#: new `Violation` field just for this handler (`Violation.message`
#: already embeds every gate's remedy text by this repo's own convention,
#: `_models.py`'s docstring).
_WAIVE004_TARGET_RULE_RE = re.compile(r"frob:waive (\S+) matches 0 findings")


def _waive004_target_rule(message: str) -> str | None:
    """The waived rule id named in a WAIVE004 `Violation.message`, or
    `None` if the message does not match the expected shape (defensive;
    should not happen against this repo's own `_waive004_violations`)."""
    match = _WAIVE004_TARGET_RULE_RE.search(message)
    return match.group(1) if match else None
