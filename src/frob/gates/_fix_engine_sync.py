"""frob.gates._fix_engine_sync -- Tier-A derived-artifact-sync auto-fix handlers.

Sibling of the `frob.gates._fix_engine_text` split (T-1646, LARGE001
residue burndown): `_fix_engine_text` keeps the LINE-scoped handlers
(FMT001, SUPPRESS001, E501) that resolve a fix by rewriting the ONE
source line a `Violation` already names; every handler in THIS module
instead resolves its fix by SYNCING one generated/derived artifact back
to its source of truth -- REG010/REL002 (registry <-> gate-rule-id and
release notes sync), SYS100 (`.strata` `may=` grant text rewrites via
`frob.strata._sync_may`'s writer), COV002 (insert a `frob:ticket`
directive above an unbound symbol), DOCENUM001 (T-1974, a `frob:
enumerates` doc anchor's `members=` claim resynced from the real
collection literal it targets, reusing `frob.gates._docenum`'s own AST
resolution), and WAIVE004 (remove a waiver already proven dead by a
fresh gate run). `TIER_A_HANDLERS` in
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

T-1916: this module also used to carry `fix_sys_interface_canonical_order`
(T-1872, `SYS-IFACE-ORDER`) -- a Tier-A handler that reordered a node's
DECLARED `interface=` names into a canonical group+alphabetical order,
never adding/removing/deduping a name (so it was not a SYS104 revival).
Retired along with `docs/design/registry/check-coverage.yaml`'s
`CHK-GATE-SYS-IFACE-ORDER` row: REG002 measured that row false (it
claimed "SYS-IFACE-ORDER is a live, enforced gate rule" while no
gate/policy rule of that id ever existed -- only this fix handler, never
registered in `frob.gates._waive._KNOWN_GATE_RULES` or `frob.gates.
_KNOWN_RULE_FIXABILITY`). Every OTHER Tier-A id in `TIER_A_HANDLERS` is
paired with a real detector somewhere (frob's own gate/audit code, or an
external tool for E501); this handler was the one exception -- a code
path silently mutating a `design/*.strata` file's declared `interface=`
presentation on every `frob ticket land`, with no detector a user could
ever see, waive, or investigate first. Building the missing detector
would mean sharing its parsing/kind-resolution logic with a NEW
self-conformance rule (the `SYS100`/`SYS108` split precedent: detector in
`frob.strata._selfconform`, fixer here) -- a genuine new feature, not a
bug fix, and disproportionate to what closed this hole. Given the
standing owner directive that no code path may auto-update declared
public-symbol surface, retiring the silently-mutating handler alongside
the false registry row was the narrower, more consistent fix.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._fix_engine_shared import FixApplied, _write_text
from frob.graph import GraphSnapshot
from frob.tickets import TicketQueue

if TYPE_CHECKING:
    from frob.gates import GateReport, GateStats

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REG010 (T-1261): a live gate rule id with no `CHK-GATE-<rule>` entry in
# check-coverage.yaml -- `frob registry audit --sync-gate-rules` names
# itself as its own remedy.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-1924
def fix_reg010_registry_sync(root: Path) -> list[FixApplied]:
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
    REG010 is wired here. T-1924: dropped the unused `snapshot` parameter
    this handler never read (T-1911's dispatch-shape fix, applied here)."""
    from frob.registry._staleness import sync_gate_rule_entries

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
# DOCENUM001 (T-1974): a `frob:enumerates` doc anchor's claimed
# `members="..."` list has drifted from the real collection literal it
# targets -- the same "registered a new id, forgot the mechanically-
# derivable doc-side bookkeeping" shape REG010 above already self-heals
# for check-coverage.yaml. Measured recurring TWICE on the identical
# gates.md rule-catalog anchor (T-1937 -> T-1958, T-1629 -> this fix) --
# a written-down "update the enumerates list too" rule did not help
# because nothing named the second edit at the moment of the first;
# auto-fixing it the same way REG010 already is closes the gap
# mechanically instead of relying on a rule being remembered.
# ---------------------------------------------------------------------------


def _docenum001_tree_for(
    root: Path, code_path: str, tree_cache: dict[str, ast.Module | None]
) -> ast.Module | None:
    """Parse (and memoize in `tree_cache`) `code_path`'s AST, mirroring
    `frob.gates._docenum`'s own `_resolve_edge_tree` memoization so
    `fix_docenum001_enumerates_sync` never re-parses a source file per
    `frob:enumerates` edge that targets it."""
    if code_path not in tree_cache:
        try:
            code_text = (root / code_path).read_text(encoding="utf-8")
            tree_cache[code_path] = ast.parse(code_text, filename=code_path)
        except (OSError, SyntaxError, UnicodeDecodeError):
            tree_cache[code_path] = None
    return tree_cache[code_path]


def _docenum001_resync_edge(
    root: Path,
    edge,  # noqa: ANN001
    tree_cache: dict[str, ast.Module | None],
    file_lines: dict[str, list[str]],
) -> FixApplied | None:
    """One `frob:enumerates` edge's own resync step: resolve its target's
    real member set, compare against the doc's claimed `members=` text,
    and rewrite the claimed line IN `file_lines` (a per-run, per-file
    accumulator so two stale edges in the same file apply against each
    other's rewrites rather than a stale on-disk read) if they differ.
    `None` if the edge does not need a rewrite -- unresolvable target,
    unsupported collection shape, or already in sync."""
    from frob.gates._docenum import _extract_members, _parse_symref, _site_from_origin

    parsed = _parse_symref(edge.target)
    if parsed is None:
        return None
    code_path, qualname = parsed
    tree = _docenum001_tree_for(root, code_path, tree_cache)
    if tree is None:
        return None
    actual = _extract_members(tree, qualname)
    if actual is None:
        return None
    claimed = frozenset(
        m.strip() for m in edge.attrs.get("members", "").split(",") if m.strip()
    )
    if claimed == actual:
        return None
    file, line = _site_from_origin(edge.origin)
    if file not in file_lines:
        try:
            doc_text = (root / file).read_text(encoding="utf-8")
        except OSError:
            return None
        file_lines[file] = doc_text.split("\n")
    lines = file_lines[file]
    if not (1 <= line <= len(lines)):
        return None
    # frob:waive PERF004 reason="actual is this edge's own target's member set, \
    # different every iteration -- nothing to hoist across edges"
    new_members = ",".join(sorted(actual))
    new_line, n = re.subn(
        r'members="[^"]*"', f'members="{new_members}"', lines[line - 1], count=1
    )
    if n == 0:
        return None
    lines[line - 1] = new_line
    return FixApplied(
        rule="DOCENUM001",
        file=file,
        line=line,
        detail=f"resynced enumerates members for {edge.target}",
    )


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-1974
def fix_docenum001_enumerates_sync(
    root: Path, snapshot: GraphSnapshot
) -> list[FixApplied]:
    """Tier-A fix (T-1974): a `frob:enumerates` doc anchor's claimed
    `members="..."` attribute is mechanically DERIVABLE from the real
    collection literal it targets -- reuses `frob.gates._docenum`'s own
    AST resolution (`_extract_members`/`_parse_symref`/`_site_from_
    origin`, the SAME functions DOCENUM001's own detector calls, via
    `_docenum001_resync_edge`) to recompute the real member set and
    rewrite the doc line's `members=` attribute to match, in place,
    rather than requiring a hand edit at land time -- the "detector in
    one module, fixer in a sibling module" split `fix_reg010_registry_
    sync` above and `_sync_may`'s SYS100 fixer both already use. Covers
    EVERY `frob:enumerates` edge in the graph, not only the gates.md
    rule-catalog anchor that motivated this fix (T-1227's own shape
    list is anchor-agnostic), so this closes the whole class rather
    than one instance. Idempotent: a member list already correct is
    left untouched."""
    from frob.graph._models import EdgeKind

    tree_cache: dict[str, ast.Module | None] = {}
    file_lines: dict[str, list[str]] = {}
    applied = [
        fix
        for edge in snapshot.edges
        if edge.kind == EdgeKind.ENUMERATES
        for fix in (_docenum001_resync_edge(root, edge, tree_cache, file_lines),)
        if fix is not None
    ]

    for file, lines in file_lines.items():
        _write_text(root / file, "\n".join(lines))

    return applied


# ---------------------------------------------------------------------------
# REL002 (T-1261): a derived release artifact disagrees with `.frob-
# release.json`'s authoritative version -- `frob release sync` names
# itself as its own remedy.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-1924
def fix_rel002_release_sync(root: Path) -> list[FixApplied]:
    """Tier-A fix (T-1261): REL002 already names its own remedy verbatim
    (`frob release sync`) -- regenerates `pyproject.toml`'s version,
    `uv.lock`, and CHANGELOG.md's skeleton entry FROM `.frob-release.
    json` (the ONE version authority), reusing the exact `frob.release`
    functions `frob release sync`'s own CLI dispatches to
    (`authoritative_version`/`rewrite_pyproject_version`/
    `changelog_skeleton_entry`, plus `uv lock` via `frob.gitio.run_argv`).
    Never writes `.frob-release.json` itself, only the three derived
    artifacts -- T-1137's anti-goal that no handler treats the manifest
    (or `frob.toml`/ratchet state) as a target it may write. T-1924:
    dropped the unused `snapshot` parameter this handler never read
    (T-1911's dispatch-shape fix, applied here)."""
    from frob.gitio import run_argv
    from frob.release import (
        authoritative_version,
        changelog_skeleton_entry,
        rewrite_pyproject_version,
    )

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
# frob:ticket T-1924
def fix_sys100_may_via_union(root: Path) -> list[FixApplied]:
    """Tier-A fix (T-1531): widen a node's `may "<kind>" via [...]` grant
    (or insert a brand-new via-scoped grant) to cover a file
    `check_capability_conformance` (SYS100 core) observed exercising an
    already-granted capability kind outside its declared `via` surface --
    `frob.strata._sync_may.sync_may_report`/`apply_sync_may`, this
    handler's own writer (T-1531, module docstring there for the scope
    cut: SYS100 EXTENDED is not handled). A design root that does not
    resolve is logged and treated as no fixes applied. T-1924: dropped
    the unused `snapshot` parameter this handler never read (T-1911's
    dispatch-shape fix, applied here)."""
    from frob.strata._sync_may import apply_sync_may, sync_may_report

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
# frob:ticket T-1924
def fix_sys100_extended_whole_node_grant(root: Path) -> list[FixApplied]:
    """Tier-A fix (T-1545): insert a bare, via-less `may "<kind>";` grant
    for a node `_extended_kind_violations` (SYS100 EXTENDED) observed
    exercising an undeclared eval/process-control/ffi/... capability --
    `frob.strata._sync_may.sync_may_extended_report`/
    `apply_sync_may_extended`, this handler's own writer (module
    docstring there for the deliberately-conservative whole-node
    rationale: EXTENDED carries no per-file evidence to narrow a `via`
    list to). A design root that does not resolve is logged and treated
    as no fixes applied. T-1924: dropped the unused `snapshot` parameter
    this handler never read (T-1911's dispatch-shape fix, applied
    here)."""
    from frob.strata._sync_may import apply_sync_may_extended, sync_may_extended_report

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
    mass-invalidation shape (`_mass_invalidation_rules`) filtered back OUT
    (`_drop_untrustworthy_mass_stale_candidates`, T-1592's unconditional
    refusal), THEN (T-1942) every archgate-family candidate this run's
    per-site examined-sites substrate did not positively confirm was
    examined also filtered back OUT (`_drop_unexamined_archgate_
    candidates`), THEN (T-2011) the same treatment for the perf family
    (`_drop_unexamined_perf_candidates`) -- a fourth, purely additive
    guard stacked on top of the first three, never a replacement for any
    of them. T-2011 investigated strata/graph/vet for the same treatment
    and found none of the three soundly wireable (see tickets.md's T-2011
    Done report) -- only perf is added here."""
    from frob.gates import GateConfig, run_gates
    from frob.gates._coverage_sites import attach_examined_sites

    result = run_gates(GateConfig(root=str(root), gates=gates, ticket=ticket))
    if result.is_err:
        _log.error(
            "WAIVE004 auto-fix: self-manufactured run_gates() errored (%s) -- "
            "deleting nothing",
            result.danger_err,
        )
        return None

    # T-1942: enrich with per-site examined-sites BEFORE deriving
    # candidates -- `_drop_unexamined_archgate_candidates` below needs
    # `report.stats.examined_sites` populated, and `run_gates` itself
    # does not populate it (T-1921 shipped the substrate deliberately
    # unwired; this is that wiring's own first production call site).
    report = attach_examined_sites(result.danger_ok, root)
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

    candidates = _drop_untrustworthy_mass_stale_candidates(root, candidates)
    candidates = _drop_unexamined_archgate_candidates(candidates, report.stats)
    return _drop_unexamined_perf_candidates(candidates, report.stats)


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


# frob:ticket T-1904
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
    few live waivers is no longer invisible to this guard either.

    T-1579 re-measured (2026-08-09) after T-1620/T-1886 closed the two
    structural gaps those tickets named: neither reintroduces a live-
    finding-shaped escape from this refusal, and `TestWaive004
    DegradedRunGuard.test_mass_invalidation_with_live_finding_elsewhere_
    still_refuses` (`tests/test_gates.py`) is a standing regression lock
    proving one still does not exist -- the exact "one live finding
    elsewhere proves the detector ran" argument this docstring's own
    T-1592 paragraph describes and measured unsafe. A sound escape would
    need proof that the specific WAIVED SITE (not just the rule, some-
    where) was actually re-analyzed this run -- per-site analysis-
    coverage tracking through every gate's optional native substrate --
    which is a materially larger undertaking than a live-finding check
    and is not implemented here; T-1579 closed on this finding (filing
    T-1904 as the successor for the coverage-tracking substrate itself)
    rather than shipping an escape already known to be unsound by
    reintroducing the one this module's own history already falsified.
    A genuinely mass-stale rule's waivers still require manual review
    and deletion; only the AUTOMATED batch delete stays refused."""
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


#: T-2011: PERF001-008 and PERF010-014 are fed exclusively from
#: `frob.perf.perf_rules(snapshot, parsed)`, where `parsed` is exactly the
#: file set `perf_gate`'s own `_perf_gate_candidate_paths` +
#: `_perf_gate_parse_files` computes (same "has a registered tree-sitter
#: grammar, and `parse_file` succeeded on it" test `frob.gates.
#: _coverage_sites._perf_examined_sites` re-derives independently) --
#: confirmed by reading `perf_gate`/`perf_rules` directly, not inferred
#: from the "perf" family name. PERF009 (`frob.perf._ratchet.
#: ratchet_violations`) is DELIBERATELY EXCLUDED: `perf_gate` reads it
#: from `.frob/perf/ratchet_findings.json`, a precomputed `frob perf
#: collect` artifact never derived from this run's own parse pass --
#: `_perf_examined_sites` reports nothing about whether that artifact is
#: fresh, so a PERF009 waiver's site being in the perf-examined set would
#: not actually mean PERF009 itself was re-evaluated this run. Including
#: PERF009 here would be the exact unsound "family name matches, so
#: assume covered" mistake this ticket's brief warns against.
_PERF_RULE_IDS = frozenset(
    {
        "PERF001",
        "PERF002",
        "PERF003",
        "PERF004",
        "PERF005",
        "PERF006",
        "PERF007",
        "PERF008",
        "PERF010",
        "PERF011",
        "PERF012",
        "PERF013",
        "PERF014",
    }
)


# frob:ticket T-2011
def _drop_unexamined_perf_candidates(
    candidates: list[tuple[str, int, str]],
    stats: "GateStats",
) -> list[tuple[str, int, str]]:
    """T-2011: a FOURTH, purely additive WAIVE004 guard, stacked on top of
    (never in place of) `_drop_unexamined_archgate_candidates` and its own
    two predecessors -- same shape as `_drop_unexamined_archgate_
    candidates`, restricted to `_PERF_RULE_IDS` (PERF001-008/010-014,
    deliberately excluding PERF009 -- see that constant's own docstring
    for why). Drops any remaining candidate whose target rule is a perf
    rule id unless `frob.gates._coverage_sites.site_examined` positively
    confirms THIS run's perf pass actually parsed the candidate's own
    file. Every candidate whose target rule is NOT in `_PERF_RULE_IDS`
    passes through completely unchanged -- same "grant nothing outside
    this family" contract `_drop_unexamined_archgate_candidates` already
    documents, only additive, never able to re-add a candidate a prior
    stage already dropped."""
    from frob.gates._coverage_sites import site_examined

    perf_rules = _PERF_RULE_IDS
    kept: list[tuple[str, int, str]] = []
    for file, line, rule in candidates:
        if rule in perf_rules and not site_examined(stats, "perf", file):
            _log.error(
                "WAIVE004 auto-fix: %s waiver at %s:%d targets a perf rule, "
                "but this run's examined-sites substrate did not confirm %s was "
                "examined -- deleting nothing for this candidate",
                rule,
                file,
                line,
                file,
            )
            continue
        kept.append((file, line, rule))
    return kept


def _archgate_rule_ids() -> frozenset[str]:
    """T-1942: every rule id `frob.gates._arch.arch_gate` can emit -- the
    complete set of rule ids the "archgate" family (the only family
    `frob.gates._coverage_sites` instruments today, T-1921) covers.
    Re-derived from `frob.gates._arch._ARCH_CATEGORY_TO_RULE`'s own
    values rather than hand-duplicated here, so a new ARCH1xx/CPPTHROW/
    LARGE-shaped category added to that map is automatically covered by
    `_drop_unexamined_archgate_candidates` below with no second edit --
    two copies of this list desyncing silently is exactly the kind of
    mistake that would make the new guard's "grants nothing outside
    archgate" contract wrong by omission instead of by design."""
    from frob.gates._arch import _ARCH_CATEGORY_TO_RULE

    return frozenset(_ARCH_CATEGORY_TO_RULE.values())


# frob:ticket T-1942
def _drop_unexamined_archgate_candidates(
    candidates: list[tuple[str, int, str]],
    stats: "GateStats",
) -> list[tuple[str, int, str]]:
    """T-1942: a THIRD, purely additive WAIVE004 guard, stacked on top of
    (never in place of) `_drop_untrustworthy_mass_stale_candidates` --
    drops any remaining candidate whose target rule belongs to the
    archgate family (`_archgate_rule_ids`) unless `frob.gates.
    _coverage_sites.site_examined` positively confirms THIS run's
    archgate pass actually examined the candidate's own file.

    Every candidate whose target rule is NOT an archgate rule id passes
    through completely unchanged -- archgate is the only family T-1921's
    substrate instruments today, so this check must GRANT NOTHING for
    any other family, never narrow a family's existing behavior just
    because `site_examined` would trivially report False for it (that
    would be indistinguishable, in effect, from silently treating an
    uninstrumented family as covered by a check it never opted into --
    the same blast radius this whole guard chain exists to prevent, just
    inverted). This is why the filter is gated on `rule in
    _archgate_rule_ids()` rather than calling `site_examined` for every
    candidate unconditionally.

    Can only ever REMOVE candidates a prior stage already proposed to
    retire -- it has no path to add one back, so it cannot make the
    overall guard chain less conservative than it already was, only
    equal or stricter, matching T-1904's incident history and this
    ticket's own explicit "additive-only" brief."""
    from frob.gates._coverage_sites import site_examined

    archgate_rules = _archgate_rule_ids()
    kept: list[tuple[str, int, str]] = []
    for file, line, rule in candidates:
        if rule in archgate_rules and not site_examined(stats, "archgate", file):
            _log.error(
                "WAIVE004 auto-fix: %s waiver at %s:%d targets an archgate rule, "
                "but this run's examined-sites substrate did not confirm %s was "
                "examined -- deleting nothing for this candidate",
                rule,
                file,
                line,
                file,
            )
            continue
        kept.append((file, line, rule))
    return kept


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
    candidates are never affected by this check either way.

    T-1942 adds a THIRD, independent, purely additive guard on top of the
    two above: `_drop_unexamined_archgate_candidates` drops any surviving
    candidate that targets an archgate-family rule
    (`frob.gates._arch.arch_gate`'s rule ids) unless this run's per-site
    examined-sites substrate (T-1921, `frob.gates._coverage_sites`)
    positively confirms the candidate's own file was actually examined
    this run -- never trusting "the rule fired somewhere" as a proxy for
    "this specific waived site was re-analyzed" (the exact unsound
    reasoning that deleted 55 live waivers once, see `_drop_
    untrustworthy_mass_stale_candidates`'s own docstring). Every OTHER
    family's candidates are completely unaffected -- archgate is the
    only family the substrate instruments today, so this guard grants
    nothing for any other family rather than narrowing its behavior."""
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
# SYS111 (T-2001): the capability-via-ratchet lock (`docs/design/registry/
# capability-via-ratchet.lock.json`) is the sibling half of the SYS100
# obligation `fix_sys100_may_via_union`/`fix_sys100_extended_whole_node_
# grant` above already self-heal (`design/frob.strata`'s own via-lists) --
# widening a node's grant there satisfies SYS100/SYS104 but leaves the
# ratchet's committed ceiling stale, so the breach surfaces on a LATER,
# unrelated land's SYS111 check instead of this one. Measured twice in one
# hour (T-1977, T-1665) before this handler existed.
# ---------------------------------------------------------------------------


def _frob_toml_tracked_at_head(root: Path) -> bool:
    """Whether `root/frob.toml` exists as a tracked file at git `HEAD`
    (T-2101): `git archive` fails its ENTIRE run (nonzero exit, no
    output) the moment any one of its pathspecs matches nothing, so
    `_archive_design_dir_at_head` must only add `frob.toml` to its
    pathspec when it is actually tracked -- never assumed present, since
    a repo bootstrap commit (or a consumer library repo with no
    `frob.toml` at all) must still fall back to archiving `design/`
    alone rather than losing the BEFORE snapshot entirely."""
    from frob import gitio

    probe = gitio.run_argv(["git", "-C", str(root), "cat-file", "-e", "HEAD:frob.toml"])
    return probe.is_ok and probe.danger_ok.returncode == 0


def _archive_design_dir_at_head(root: Path, dest: Path) -> bool:
    """Materialize `root`'s `design/` tree (plus `frob.toml`, T-2101) AT
    GIT HEAD into `dest` via `git archive` (T-2001, split out of
    `_capability_counts_at_head` to keep both under ARCH001's
    threshold). Returns whether the archive+extract actually succeeded
    -- `False` (never raises) on any git spawn failure, non-zero exit,
    or extraction error, the caller's own signal to give up on a BEFORE
    snapshot entirely rather than guess.

    T-2101: `frob.toml` travels alongside `design/` now (when tracked at
    HEAD, `_frob_toml_tracked_at_head`) so the scratch extraction the
    caller's `load_design_ids(extract_dir, "design")` call reads carries
    the SAME `[graph].exclude` configuration the live/current-tree call
    already has -- without it, `frob.excludes.load_exclude_globs` finds
    no `frob.toml` at all and returns `()`, so `design/litmus/**`'s
    fixture files (deliberately id-colliding across files, T-0130) leak
    into the merged elaboration and fail closed with `DuplicateId`
    (observed live: an ERROR log line naming a dozen litmus node ids on
    every land, and the BEFORE snapshot silently going empty every
    time)."""
    from frob import gitio

    archive_path = dest / "head.tar"
    pathspec = (
        ["design", "frob.toml"] if _frob_toml_tracked_at_head(root) else ["design"]
    )
    archived = gitio.run_argv(
        [
            "git",
            "-C",
            str(root),
            "archive",
            "--format=tar",
            "HEAD",
            "--output",
            str(archive_path),
            "--",
            *pathspec,
        ]
    )
    if archived.is_err or archived.danger_ok.returncode != 0:
        _log.info(
            "tier-a fixes: SYS111 ratchet sync: could not archive design/ "
            "at HEAD (%s) -- skipping (no BEFORE baseline to attribute "
            "growth to)",
            archived.danger_err
            if archived.is_err
            else archived.danger_ok.stderr.strip(),
        )
        return False
    extract_dir = dest / "extracted"
    extract_dir.mkdir()
    try:
        with tarfile.open(archive_path) as tar:
            tar.extractall(extract_dir)  # noqa: S202 -- our own repo's own history
    except (tarfile.TarError, OSError) as exc:
        _log.warning(
            "tier-a fixes: SYS111 ratchet sync: could not extract HEAD's "
            "design/ archive: %s -- skipping",
            exc,
        )
        return False
    return True


def _capability_counts_at_head(root: Path) -> "dict[str, int] | None":
    """`capability_via_site_counts` computed from `design/`'s content at
    git HEAD (T-2001) -- the BEFORE snapshot `fix_sys111_capability_
    ratchet_sync` diffs the CURRENT working tree against, to attribute
    ratchet growth to THIS land specifically rather than to history.

    Materializes HEAD's `design/` tree into a scratch directory
    (`_archive_design_dir_at_head`, never a second, parallel strata-
    parsing implementation over git blob text) so the EXACT SAME `load_
    design_ids`/`merge_models` loader the live model uses also produces
    the historical one.

    Returns `None` (skip the caller entirely) only when the archive
    itself could not be produced at all -- no `HEAD`, not a git repo, a
    spawn failure. An archive that succeeds but contains no `design/`
    files correctly returns `{}` (a real, meaningful "nothing existed
    here at HEAD," under which every currently-observed site counts as
    this land's own growth -- e.g. a land that adds `design/` for the
    first time)."""
    from frob.strata import merge_models
    from frob.strata._design_load import load_design_ids
    from frob.strata._effects import capability_via_site_counts

    with tempfile.TemporaryDirectory(prefix="frob-sys111-head-") as tmp_str:
        tmp = Path(tmp_str)
        if not _archive_design_dir_at_head(root, tmp):
            return None
        extract_dir = tmp / "extracted"
        if not (extract_dir / "design").is_dir():
            return {}
        ids = load_design_ids(extract_dir, "design")
        if ids.errors or not ids.models:
            return {}
        return capability_via_site_counts(merge_models(ids.models))


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys111_bumps_growth_this_lands_diff_caused kind="unit"  # noqa: E501
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_sys111_leaves_a_pre_existing_breach_untouched kind="unit"  # noqa: E501
# frob:ticket T-2001
def fix_sys111_capability_ratchet_sync(root: Path) -> list[FixApplied]:
    """Tier-A fix (T-2001): re-baseline `capability-via-ratchet.lock.json`'s
    `accepted_count` for exactly the `(node, atom)` pairs whose scoped
    via-list site count GREW between this land's own git-committed parent
    (`_capability_counts_at_head`) and the CURRENT working tree -- run
    AFTER `fix_sys100_may_via_union`/`fix_sys100_extended_whole_node_grant`
    in `TIER_A_HANDLERS`' declared order, so the current-side count
    already reflects whatever those two just widened in `design/
    frob.strata`.

    Never bumps unconditionally to whatever is currently observed --
    that would turn the ratchet into a no-op that ratifies any growth,
    the exact anti-goal T-2001's own body names. A `(node, atom)` pair
    whose CURRENT count exceeds the committed ceiling but did NOT grow
    since HEAD is a PRE-EXISTING breach (inherited from before this land
    touched anything) and is deliberately left untouched -- still a
    violation, still surfaced by SYS111 exactly as before (T-2001's own
    acceptance criterion 3).

    Every bump records WHY, verbatim in the lock entry's own `reason`
    field (`T-2001 auto-baseline: ...`) and `ticket: "T-2001"` -- the same
    accountability the module docstring's "explicit, recorded
    justification" language already demands of a human-authored widening,
    now produced mechanically for the one case that IS mechanically
    derivable (this land's own measured diff), never for a wider one.

    Known, disclosed first-cut gap: a hand-edited via-list widening the
    agent already COMMITTED on their own worktree branch before landing
    is invisible to this HEAD-relative diff (HEAD already includes it).
    Both measured occurrences (T-1977, T-1665) were caused by SYS100's
    OWN auto-fix widening an UNCOMMITTED via-list in the SAME Tier-A
    pass, which this fully covers; a committed hand-edit would need a
    true pre-land-tip base ref threaded through (the shape `frob.
    tickets._land.land`'s `sync_gate_rules` callback already uses) to
    close completely -- left as documented residue, not smuggled into
    this fix's own scope.

    Best-effort like every sibling handler in this module: any git/parse
    failure computing the BEFORE snapshot skips this handler entirely (no
    bump at all), matching the ratchet's own deny-by-default posture --
    "cannot prove this land caused it" must never become "assume it
    did"."""
    if not (root / "design").is_dir():
        return []
    from frob.strata import merge_models
    from frob.strata._design_load import load_design_ids
    from frob.strata._effects import capability_via_site_counts as _current_counts

    current_ids = load_design_ids(root, "design")
    if current_ids.errors or not current_ids.models:
        return []
    current_counts = _current_counts(merge_models(current_ids.models))
    if not current_counts:
        return []

    before_counts = _capability_counts_at_head(root)
    if before_counts is None:
        return []

    return _apply_capability_ratchet_bumps(root, current_counts, before_counts)


def _raw_capability_ratchet_lock(lock_path: Path) -> dict:
    """`lock_path`'s parsed JSON with a guaranteed `"entries"` dict key
    (T-2001, split out of `_apply_capability_ratchet_bumps` to keep it
    under ARCH001's line threshold, zero behavior change) -- `{"entries":
    {}}` shape on any missing-file/parse/malformed-shape surprise,
    never raises. Distinct from `_load_capability_ratchet_lock` (which
    returns just the entries mapping, best-effort `{}` on failure): this
    keeps the WHOLE parsed document (`generated_by`/`schema_version`
    etc.) so the caller's write-back preserves every field it did not
    itself touch."""
    try:
        raw = (
            json.loads(lock_path.read_text(encoding="utf-8"))
            if lock_path.is_file()
            else {}
        )
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    if not isinstance(raw.get("entries"), dict):
        raw["entries"] = {}
    return raw


def _apply_capability_ratchet_bumps(
    root: Path, current_counts: "dict[str, int]", before_counts: "dict[str, int]"
) -> list[FixApplied]:
    """The load-lock/compute-bumps/write half of `fix_sys111_capability_
    ratchet_sync` (T-2001: split out to keep the parent under ARCH001's
    line threshold, zero behavior change) -- `current_counts`/`before_
    counts` are the AFTER/BEFORE `capability_via_site_counts` snapshots
    the caller already computed. A `(node, atom)` pair is bumped only
    when its current count exceeds the committed ceiling AND grew since
    `before_counts` -- a pair already exceeding the ceiling but unchanged
    since `before_counts` is a PRE-EXISTING breach, left untouched (still
    surfaced by SYS111) rather than silently ratified."""
    from frob.strata._effects import (
        CAPABILITY_RATCHET_LOCK_REL,
        _load_capability_ratchet_lock,
    )

    lock_path = root / CAPABILITY_RATCHET_LOCK_REL
    lock_entries = _load_capability_ratchet_lock(root)
    raw = _raw_capability_ratchet_lock(lock_path)

    applied: list[FixApplied] = []
    for key, count in sorted(current_counts.items()):
        entry = lock_entries.get(key)
        accepted_raw = entry.get("accepted_count") if isinstance(entry, dict) else None
        accepted = accepted_raw if isinstance(accepted_raw, int) else 0
        if count <= accepted:
            continue
        if count <= before_counts.get(key, 0):
            # Pre-existing breach: already this high (or higher) before
            # this land's own diff touched anything -- not attributable
            # here, leave it violating for a human to disposition, per
            # T-1977's own precedent and T-2001's acceptance criterion 3.
            continue
        node_id, atom = key.split("::", 1)
        raw["entries"][key] = {
            "accepted_count": count,
            "reason": (
                f"T-2001 auto-baseline: this land's own diff grew {atom} on "
                f"{node_id} from {before_counts.get(key, 0)} to {count} "
                "site(s) (fix_sys111_capability_ratchet_sync)"
            ),
            "ticket": "T-2001",
        }
        applied.append(
            FixApplied(
                rule="SYS111",
                file=CAPABILITY_RATCHET_LOCK_REL,
                line=0,
                detail=f"{key} accepted_count {accepted} -> {count}",
            )
        )
    if not applied:
        return []
    _write_text(lock_path, json.dumps(raw, indent=2, sort_keys=True) + "\n")
    return applied
