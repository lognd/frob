"""frob.gates._fix_engine_sync -- Tier-A derived-artifact-sync auto-fix handlers.

Sibling of the `frob.gates._fix_engine_text` split (T-1646, LARGE001
residue burndown): `_fix_engine_text` keeps the LINE-scoped handlers
(FMT001, SUPPRESS001, E501) that resolve a fix by rewriting the ONE
source line a `Violation` already names; every handler in THIS module
instead resolves its fix by SYNCING one generated/derived artifact back
to its source of truth -- REG010/REL002 (registry <-> gate-rule-id and
release notes sync), SYS100 (`.strata` `may=` grant text rewrites via
`frob.strata._sync_may`'s writer), COV002 (insert a `frob:ticket`
directive above an unbound symbol), and WAIVE004 (remove a waiver
already proven dead by a fresh gate run). `TIER_A_HANDLERS` in
`_fix_engine` imports every public `fix_*` symbol from both this module
and `_fix_engine_text` and dispatches through the same uniform `(root,
snapshot, queue, ticket_id) -> list[FixApplied]` call shape every handler
uses -- this split changes no behavior, only which file a given handler's
body lives in.

T-1870: this module used to also carry `fix_sys104_interface_union`, the
Tier-A auto-fix for SYS104 (a node's declared `interface=` attrs drifting
from its measured real public surface). Deleted along with the rest of
the `frob sys sync-interface` machinery per an explicit owner directive
("we shouldn't auto-update the public symbols") -- `interface=` is no
longer auto-written by anything, anywhere, including at land time. SYS108
(a node's `interface=` attrs declaring the same symbol twice) is a
DIFFERENT rule -- a well-formedness check on the declared value, not a
mirror-of-code check -- and was never auto-fixed by this module in the
first place; it is unaffected by this cut.
"""

from __future__ import annotations

import ast
import logging
import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._fix_engine_shared import FixApplied, _write_text
from frob.graph import GraphSnapshot
from frob.tickets import TicketQueue

if TYPE_CHECKING:
    from frob.gates import GateReport
    from frob.strata._code_binding import CodeBinding

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
# SYS100 core (T-1531): a net/fs-write/exec effect observed in a file with
# no `may "<kind>" via [...]` grant covering it -- widen (or create) the
# grant's `via` list to include the observed file, sorted union, via the
# `frob.strata._sync_may` writer (module docstring there: SYS100's
# EXTENDED case, eval/process-control/ffi/..., has no per-file evidence to
# add and is deliberately NOT handled here).
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys100_may_via_union_applies_via_apply_tier_a_fixes  # noqa: E501
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_sys100_no_design_dir_is_a_no_op
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


# ---------------------------------------------------------------------------
# SYS100 extended (T-1545): eval/process-control/ffi/install-hook/sql/
# deserialize/html_render/fetch_url/client_storage -- no per-file evidence,
# so `frob.strata._sync_may.sync_may_extended_report` inserts a
# deliberately conservative WHOLE-NODE (via-less) `may "<kind>";` grant
# instead of guessing a `via` file (T-1531's `fix_sys100_may_via_union`
# CORE case, above, is the only handler that can narrow to a `via` list at
# all -- see that module's docstring for why EXTENDED structurally
# cannot).
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys100_extended_whole_node_grant_applies_via_apply_tier_a_fixes  # noqa: E501
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_sys100_extended_no_design_dir_is_a_no_op
# frob:ticket T-1545
def fix_sys100_extended_whole_node_grant(
    root: Path, snapshot: GraphSnapshot
) -> list[FixApplied]:
    """Tier-A fix (T-1545): insert a bare, via-less `may "<kind>";` grant
    for a node `_extended_kind_violations` (SYS100 EXTENDED) observed
    exercising an undeclared eval/process-control/ffi/... capability --
    `frob.strata._sync_may.sync_may_extended_report`/
    `apply_sync_may_extended`, this handler's own writer (module
    docstring there for the deliberately-conservative whole-node
    rationale: EXTENDED carries no per-file evidence to narrow a `via`
    list to). A design root that does not resolve is logged and treated
    as no fixes applied."""
    from frob.strata._sync_may import apply_sync_may_extended, sync_may_extended_report

    del snapshot  # signature uniformity only, this handler reads the design tree itself
    if not (root / "design").is_dir():
        return []
    report = sync_may_extended_report(root, "design")
    if report.is_err:
        _log.warning(
            "tier-a fixes: SYS100 extended sync-may skipped: %s", report.danger_err
        )
        return []
    result = report.danger_ok
    if not result.has_drift:
        return []
    written = apply_sync_may_extended(root, result)
    applied: list[FixApplied] = []
    for file_result in result.files:
        if file_result.path not in written:
            continue
        for diff in file_result.diffs:
            applied.append(
                FixApplied(
                    rule="SYS100",
                    file=file_result.path,
                    line=0,
                    detail=f"node {diff.node} may {diff.kind!r} (whole-node grant)",
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


# frob:doc docs/modules/gates.md#fix_cov002_ticket_directive_insertion-auto-fix-t-1548
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
#:
#: T-1620: this absolute count is STRUCTURALLY BLIND to any rule with
#: fewer than this many live waivers total -- a rule with exactly 2 live
#: `frob:waive` directives can never reach 5 candidates no matter how
#: degraded the run is, so both of its waivers silently pass through
#: this guard and get deleted. `_mass_invalidation_rules` below now also
#: flags the PROPORTIONAL case (every one of a rule's live waivers going
#: stale in the same run) regardless of the raw count -- 2 of 2 is at
#: least as suspicious as 40 of 40, arguably more so.
_WAIVE004_MASS_INVALIDATION_THRESHOLD = 5

#: T-1886: the PROPORTIONAL check below is a sample-size argument ("all of
#: this rule's live waivers going stale together is suspicious regardless
#: of count") and, like any sample-size argument, has no discriminating
#: power at `N=1` -- a rule with exactly one live `frob:waive` directive
#: reads as "100% went stale" the instant that single waiver is genuinely
#: dead, indistinguishable from a degraded run by construction. Without a
#: floor this makes `fix_waive004_stale_waiver` structurally unable to
#: ever delete a lone dead waiver for a low-traffic rule -- not a rare
#: edge case, since a repo with exactly one live waiver for some rule is
#: an entirely ordinary state, not itself a degradation signal. Mirrors
#: the `_DEFLATION_MIN_KNOWN_MODULES` precedent (`frob.gates._coverage`):
#: below a minimum sample size, the check simply does not fire rather
#: than firing on noise. Chosen at 2 (not the absolute threshold's 5) so
#: the guard keeps its full bite the moment there is ANY sample size to
#: reason about proportionally -- 2-of-2 and up still trip it exactly as
#: before; only the N=1 case, which carries no proportional signal at
#: all, now falls through to the (also fully intact) absolute-threshold
#: check alone.
_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT = 2

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


def _mass_invalidation_rules(
    candidates: list[tuple[str, int, str]], live_counts: dict[str, int]
) -> dict[str, int]:
    """Every target rule in `candidates` (each a `(file, line, rule)`
    WAIVE004 deletion candidate) that looks like a mass-invalidation
    signature, mapped to its candidate count -- the T-1323 incident's own
    shape (one rule family's waivers ALL going stale in the same run)
    treated as anomalous-zero-findings evidence in its own right, without
    needing a separately recorded baseline pool to compare against.
    Returns EVERY rule meeting either check (not just the first), so
    `_drop_untrustworthy_mass_stale_candidates` can report and drop each
    one by name.

    Two independent triggers (T-1620 adds the second):
    - ABSOLUTE: candidate count >= `_WAIVE004_MASS_INVALIDATION_THRESHOLD`
      (T-1323's original guard).
    - PROPORTIONAL: `live_counts[rule]` (this rule's total live
      `frob:waive` directives, from `_waivers_by_rule` over the SAME
      snapshot this run measured) is at least
      `_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT` and EVERY one of them is a
      candidate this run -- structurally invisible to the absolute
      threshold for any rule with fewer than
      `_WAIVE004_MASS_INVALIDATION_THRESHOLD` live waivers, and just as
      much the T-1323 incident's own shape at any count above the floor:
      a rule with 2 live waivers both going stale in the same run is the
      same signature as 40 of 40, not weaker evidence just because there
      were fewer to begin with. T-1886: below the floor (i.e. `N=1`) the
      ratio carries no proportional signal at all -- see
      `_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT`'s own docstring -- so it is
      excluded rather than treated as maximally suspicious."""
    counts: dict[str, int] = {}
    for _file, _line, rule in candidates:
        counts[rule] = counts.get(rule, 0) + 1
    return {
        rule: count
        for rule, count in counts.items()
        if count >= _WAIVE004_MASS_INVALIDATION_THRESHOLD
        or (
            live_counts.get(rule, 0) >= _WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT
            and count >= live_counts[rule]
        )
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

    return _drop_untrustworthy_mass_stale_candidates(root, candidates)


def _live_waiver_counts(root: Path) -> dict[str, int]:
    """T-1620: every rule id's total live `frob:waive` directive count in
    `root`'s current tree (`frob.gates._waive._waivers_by_rule` over a
    freshly built `GraphSnapshot`) -- the denominator
    `_mass_invalidation_rules`'s proportional check needs to tell "every
    one of this rule's 2 live waivers went stale" from "2 of this rule's
    40 live waivers went stale". Best-effort: a build failure returns an
    empty mapping (the proportional check then simply never fires,
    falling back to the absolute-threshold check alone -- never worse
    than before this ticket, never a crash)."""
    from frob.gates._waive import _waivers_by_rule
    from frob.graph import build_graph

    cache = root / ".frob" / "cache.db"
    result = build_graph(root, cache)
    if result.is_err:
        _log.debug(
            "_live_waiver_counts: build_graph failed (%s) -- proportional "
            "mass-invalidation check disabled this run",
            result.danger_err,
        )
        return {}
    return {
        rule: len(edges) for rule, edges in _waivers_by_rule(result.danger_ok).items()
    }


def _drop_untrustworthy_mass_stale_candidates(
    root: Path,
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
    a land. T-1578 (frob_core-only) did not cover this; T-1620 extends the
    degraded-run signal to `strata_core` too (`_perf_reach_degraded_marker`
    in `frob.gates`) and adds the proportional check below, so a rule with
    few live waivers is no longer invisible to this guard either."""
    live_counts = _live_waiver_counts(root)
    mass_rules = _mass_invalidation_rules(candidates, live_counts)
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


# ---------------------------------------------------------------------------
# SYS-interface canonical order (T-1872): reorder a node's DECLARED
# `interface=` names -- classes, then functions, then constants, then
# unresolved, alphabetical within each group -- never add, remove, or
# dedup a name.
#
# NOT a revival of `sync_interface`/SYS104 (T-1870, deleted): that writer
# DERIVED the declared set from measured real code (accounting). This
# handler never consults code to decide MEMBERSHIP -- it only consults
# code to classify a name a human already declared as class/function/
# const, purely to choose where that name sorts. Content (which names
# appear, how many times) is asserted identical before and after
# (`_assert_same_multiset`); the fix silently no-ops rather than write a
# different set, and T-1871's duplicate-value PARSE ERROR (dropped, but
# the invariant still holds here defensively) is never swallowed by a
# quiet dedup.
# ---------------------------------------------------------------------------

#: One node OR store header line -- mirrors the deleted
#: `_sync_interface._NODE_HEADER_RE` byte-for-byte (T-1425's store
#: coverage included), reimplemented here rather than imported since that
#: module no longer exists (T-1870).
_IFACE_NODE_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:node|store)\s+(?P<id>\S+)\b[^{]*\{\s*$"
)

#: Legacy one-`attr interface=<name>;`-per-line form, still readable
#: (never written by this handler -- `_render_interface_block` below
#: always writes the compact T-1198 bracket-list form, same posture the
#: deleted writer took).
_IFACE_LEGACY_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)attr interface=(?P<name>\S+?);\s*$"
)

#: T-1198 compact `attr interface=[...]` block open/close markers.
_IFACE_BLOCK_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)attr interface=\[\s*$")
_IFACE_BLOCK_CLOSE_RE = re.compile(r"^[ \t]*\];\s*$")

#: Symbol names packed per wrapped line inside a rewritten `interface=[...]`
#: block -- matches the deleted `_sync_interface.NAMES_PER_LINE` value so a
#: canonical-order rewrite looks like the same convention T-1198 already
#: established, not a second competing wrap width.
_IFACE_NAMES_PER_LINE = 6

#: Canonical group order for `_canonical_interface_key`: classes first,
#: then functions, then constants/other module-level assignments, then
#: names this handler could not resolve against any bound `.py` file at
#: all (kept LAST and alphabetical -- "cannot verify is never verified",
#: per this ticket's spec, never guessed into a group).
_IFACE_GROUP_ORDER = {"class": 0, "function": 1, "const": 2, "unresolved": 3}


# frob:waive DUP001 reason="byte-identical to _sync_may.py::_node_body_span by \
# construction -- both independently mirror the deleted _sync_interface.py's own \
# _node_body_span, a tiny (7-line) brace-depth scanner with no state to share; \
# extracting a shared helper would need a new module both _sync_may.py (SYS100, not in \
# T-1872's scope) and this handler import from, which is a real refactor outside this \
# order-only ticket's declared scope -- filed as a follow-up, not silently done here"
def _iface_node_body_span(lines: list[str], header_idx: int) -> int:
    """The line index of the `}` closing the node body opened at
    `lines[header_idx]`, brace-depth matched (mirrors the deleted
    `_sync_interface._node_body_span`)."""
    depth = 1
    for idx in range(header_idx + 1, len(lines)):
        # frob:waive PERF002 reason="each line is a different string every iteration \
        # -- nothing to hoist or cache; one-pass O(n) brace-depth scan, not a repeated \
        # identical query"
        depth += lines[idx].count("{") - lines[idx].count("}")
        if depth == 0:
            return idx
    return len(lines) - 1  # malformed input: no matching close, best effort


#: One located `interface=` declaration span: `(first_line, last_line,
#: indent, names, is_compact)`.
_IfaceSpan = tuple[int, int, str, list[str], bool]


def _iface_find_spans(
    lines: list[str], header_idx: int, close_idx: int
) -> list[_IfaceSpan]:
    """Locate every `interface=` declaration inside one node's body, in
    whichever form (compact block or legacy per-line) each is written --
    mirrors the deleted `_sync_interface._find_interface_spans`
    (T-1624's multi-span collapse precedent) so a node with more than one
    physical declaration still gets merged into exactly one block, with
    its full multiset of names preserved."""
    spans: list[_IfaceSpan] = []
    idx = header_idx + 1
    while idx < close_idx:
        open_m = _IFACE_BLOCK_OPEN_RE.match(lines[idx])
        if open_m is not None:
            names: list[str] = []
            close_idx_inner = idx
            for j in range(idx + 1, close_idx):
                if _IFACE_BLOCK_CLOSE_RE.match(lines[j]):
                    close_idx_inner = j
                    break
                names.extend(
                    part.strip() for part in lines[j].split(",") if part.strip()
                )
            spans.append((idx, close_idx_inner, open_m.group("indent"), names, True))
            idx = close_idx_inner + 1
            continue
        legacy_m = _IFACE_LEGACY_LINE_RE.match(lines[idx])
        if legacy_m is not None:
            spans.append(
                (idx, idx, legacy_m.group("indent"), [legacy_m.group("name")], False)
            )
        idx += 1
    return spans


def _node_symbol_kinds(
    binding: "CodeBinding", root: Path, node_id: str
) -> dict[str, str]:
    """Classify every top-level `.py` symbol name bound to `node_id` as
    `"class"`, `"function"`, or `"const"` (plain module-level assignment/
    annotated assignment) -- purely for canonical-order GROUPING, never
    for deciding whether a declared `interface=` name stays or goes. A
    name defined more than once across the node's bound files with
    DIFFERING kinds is dropped from the map entirely (ambiguous ->
    caller treats it as unresolved, never guesses)."""
    kinds: dict[str, str | None] = {}
    for rel in sorted(binding.owner):
        if binding.owner[rel] != node_id or not rel.endswith(".py"):
            continue
        path = root / rel
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, OSError, UnicodeDecodeError) as exc:
            _log.warning(
                "tier-a fixes: SYS-interface-order could not parse %s: %s", path, exc
            )
            continue
        for stmt in tree.body:
            found: dict[str, str] = {}
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[stmt.name] = "function"
            elif isinstance(stmt, ast.ClassDef):
                found[stmt.name] = "class"
            elif isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        found[t.id] = "const"
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                found[stmt.target.id] = "const"
            for name, kind in found.items():
                if name in kinds and kinds[name] not in (None, kind):
                    kinds[name] = None  # ambiguous across files -- unresolved
                elif name not in kinds:
                    kinds[name] = kind
    return {name: kind for name, kind in kinds.items() if kind is not None}


def _canonical_interface_key(name: str, kind_map: dict[str, str]) -> tuple[int, str]:
    """Sort key for one declared `interface=` name: `(group, lowercased
    name)`. `group` comes from `_IFACE_GROUP_ORDER`, keyed off `kind_map`
    (resolved symbol kind) -- an unresolved name (not in `kind_map`)
    always sorts into the trailing `"unresolved"` group, never guessed
    from lexical casing (this repo's SYMBOLIC NEVER LEXICAL rule, T-1662)."""
    kind = kind_map.get(name, "unresolved")
    group = _IFACE_GROUP_ORDER.get(kind, _IFACE_GROUP_ORDER["unresolved"])
    return (group, name.lower())


def _render_interface_block(indent: str, ordered_names: list[str]) -> list[str]:
    """Render `ordered_names` (already in final canonical order, NOT
    re-sorted here) as one compact `attr interface=[...]` block,
    `_IFACE_NAMES_PER_LINE` names per wrapped line -- mirrors the deleted
    `_sync_interface._render_interface_block`'s wrap convention exactly,
    except the caller supplies the order (that one always alphabetized
    the full set; this one groups-then-alphabetizes and must not
    re-sort, or a duplicate value could silently move group)."""
    if not ordered_names:
        return [f"{indent}attr interface=[];"]
    body_indent = indent + "    "
    out = [f"{indent}attr interface=["]
    for start in range(0, len(ordered_names), _IFACE_NAMES_PER_LINE):
        chunk = ordered_names[start : start + _IFACE_NAMES_PER_LINE]
        out.append(body_indent + ", ".join(chunk) + ",")
    out.append(f"{indent}];")
    return out


def _reorder_node_interface_block(
    lines: list[str], header_idx: int, kind_map: dict[str, str]
) -> tuple[list[str], bool]:
    """Reorder one node's declared `interface=` name(s) into canonical
    group+alphabetical order (`_canonical_interface_key`), collapsing
    multiple spans into one compact block same as T-1198's writer did --
    ORDER-ONLY: asserts the multiset of names is identical before and
    after (`Counter` comparison) and refuses the rewrite (returns
    `lines` unchanged, `False`) rather than ever write a different set.
    Returns `(new_lines, changed)`."""
    close_idx = _iface_node_body_span(lines, header_idx)
    spans = _iface_find_spans(lines, header_idx, close_idx)
    if not spans:
        return lines, False

    declared: list[str] = [name for span in spans for name in span[3]]
    ordered = sorted(declared, key=lambda n: _canonical_interface_key(n, kind_map))

    if Counter(declared) != Counter(ordered):
        _log.error(
            "tier-a fixes: SYS-interface-order refused a rewrite that would change "
            "the declared multiset (node header at line %d) -- this must never "
            "happen; leaving the block untouched",
            header_idx,
        )
        return lines, False

    single_clean = len(spans) == 1 and spans[0][4] and spans[0][3] == ordered
    if single_clean:
        return lines, False

    indent = spans[0][2]
    new_block = _render_interface_block(indent, ordered)
    new_lines = list(lines)
    for first, last, _, _, _ in reversed(spans):
        del new_lines[first : last + 1]
    insert_at = spans[0][0]
    new_lines[insert_at:insert_at] = new_block
    return new_lines, True


# frob:doc docs/strata/surface.md#interface-canonical-order-tier-a-t-1872
# frob:tests \
# tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_groups_by_kind_then_alpha  # noqa: E501
# frob:tests \
# tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_order_only_multiset_preserved_and_idempotent  # noqa: E501
# frob:ticket T-1872
def _reorder_iface_one_file(
    abs_path: Path, root: Path, binding: "CodeBinding"
) -> list[FixApplied]:
    """Reorder every node's `interface=` block inside ONE `.strata` file
    (`_reorder_node_interface_block` per node header found), writing the
    file back only if at least one node actually changed -- split out of
    `fix_sys_interface_canonical_order` purely to keep that function under
    this repo's own ARCH001 line-count threshold; no behavior seam here,
    just where the loop body lives."""
    try:
        text = abs_path.read_text(encoding="utf-8")
    except OSError:
        return []
    if "node " not in text and "store " not in text:
        return []
    rel = abs_path.relative_to(root).as_posix()
    lines = text.splitlines()
    header_idxs = [
        i for i, line in enumerate(lines) if _IFACE_NODE_HEADER_RE.match(line)
    ]
    offset = 0
    file_changed = False
    applied: list[FixApplied] = []
    for header_idx in header_idxs:
        idx = header_idx + offset
        m = _IFACE_NODE_HEADER_RE.match(lines[idx])
        if m is None:
            continue
        node_id = m.group("id")
        kind_map = _node_symbol_kinds(binding, root, node_id)
        before_len = len(lines)
        lines, changed = _reorder_node_interface_block(lines, idx, kind_map)
        if changed:
            file_changed = True
            offset += len(lines) - before_len
            applied.append(
                FixApplied(
                    rule="SYS-IFACE-ORDER",
                    file=rel,
                    line=header_idx + 1,
                    detail=f"node {node_id} interface= reordered to canonical order",
                )
            )
    if file_changed:
        new_text = "\n".join(lines)
        if text.endswith("\n") and not new_text.endswith("\n"):
            new_text += "\n"
        _write_text(abs_path, new_text)
    return applied


# frob:doc docs/strata/surface.md#interface-canonical-order-tier-a-t-1872
# frob:tests \
# tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_groups_by_kind_then_alpha  # noqa: E501
# frob:tests \
# tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_order_only_multiset_preserved_and_idempotent  # noqa: E501
# frob:ticket T-1872
def fix_sys_interface_canonical_order(
    root: Path, snapshot: GraphSnapshot
) -> list[FixApplied]:
    """Tier-A fix (T-1872): reorder every node's declared `interface=`
    names into canonical order -- resolved symbol kind (class, function,
    const), then alphabetical within each kind, unresolved names trailing
    in stable alphabetical order -- WITHOUT ever adding, removing, or
    deduping a name (module-level docstring above for why this is not a
    `sync_interface`/SYS104 revival). A design root that does not resolve,
    or that carries no node with an `interface=` declaration at all, is a
    no-op. Per-file work lives in `_reorder_iface_one_file`."""
    from frob.strata._code_binding import bind_code
    from frob.strata._design_load import DEFAULT_DESIGN_DIR, load_design_ids
    from frob.strata._sysdoc import merge_models

    del snapshot  # signature uniformity only, this handler reads the design tree itself
    if not (root / DEFAULT_DESIGN_DIR).is_dir():
        return []
    ids = load_design_ids(root, DEFAULT_DESIGN_DIR)
    if ids.errors or not ids.models:
        return []
    model = merge_models(ids.models)
    binding_result = bind_code(model, root)
    if binding_result.is_err:
        _log.warning(
            "tier-a fixes: SYS-interface-order skipped, code binding failed: %s",
            binding_result.danger_err,
        )
        return []
    binding = binding_result.danger_ok

    applied: list[FixApplied] = []
    design_root = root / DEFAULT_DESIGN_DIR
    # frob:waive WALK001 reason="design/ is a small, hand-authored .strata source \
    # subtree with no nested .git/.venv/node_modules/build/dist/target to prune -- \
    # excludes.walk_pruned would add a filter that never fires here, not change \
    # behavior; matches the deleted _sync_interface.py precedent's own waiver"
    for abs_path in sorted(design_root.rglob("*.strata")):
        applied.extend(_reorder_iface_one_file(abs_path, root, binding))
    return applied
