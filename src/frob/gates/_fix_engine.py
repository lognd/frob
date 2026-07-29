"""frob.gates._fix_engine -- Tier-A deterministic auto-fix handlers (T-1138).

First concrete slice of the T-1137 `--fix` epic, restricted to the three
fix classes with unambiguous, semantics-preserving, deterministic
rewrites and a repeated main-redding incident history: DOC007's pytest-
`::`-form `frob:tests` directives (dotted-form rewrite), DOC002's
unique-fuzzy-match anchor-slug corrections, and TICK002's draft-survived-
onto-main renumber. Every handler here is Tier-A per T-1137's own
acceptance: it either performs the ONE correct rewrite or does nothing at
all -- never a guess, never a waiver. Wiring these handlers behind an
actual `frob check --fix` CLI flag is a later batch of the same epic
(this ticket's scope is `src/frob/gates/**`/`src/frob/tickets/**`/
`tests/test_gates.py`, not `src/frob/app/**`/`src/frob/_cli_parsers/**`);
`apply_tier_a_fixes` is this module's callable entry point, ready for
that CLI batch to call directly.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_fix_engine.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (docstrings and comments describing already-implemented \
# internal behavior, verifiable by reading the code they annotate) rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- new T-1138 module documenting its own tier \
# contract"

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from frob.graph import EdgeKind, GraphSnapshot
from frob.tickets import TicketQueue
from frob.tickets._provisional import is_draft_id

if TYPE_CHECKING:
    from frob.gates import GateReport

_log = logging.getLogger(__name__)


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
class FixApplied(BaseModel):
    """One Tier-A fix `apply_tier_a_fixes` actually made: which rule it
    resolves, where, and a one-line human-readable summary of the
    rewrite -- the disclosed audit trail every fix must leave (T-1137's
    own "no silent auto-discharge" anti-goal, applied to what WAS
    auto-fixed rather than only what was left alone)."""

    model_config = {}

    rule: str
    file: str
    line: int
    detail: str


# ---------------------------------------------------------------------------
# DOC007: pytest `Class::method` collect-only separator -> this graph's own
# single-`::`-then-dotted `Class.method` convention.
# ---------------------------------------------------------------------------

#: Mirrors `frob.gates._docptr._DOUBLE_SEP_TESTS_TARGET_RE` exactly (a
#: `frob:tests` target's SECOND `::` is the pytest-collect-only-form
#: mistake DOC007 flags) -- not imported from there to avoid a second
#: entry point into that module's private regex; both are the same
#: literal pattern by construction, covered by
#: `test_doc007_dotted_form_regex_matches_docptr_precedent` below.
_DOUBLE_SEP_TESTS_TARGET_RE = re.compile(r"::[^:]*::")


def _dotted_form(target: str) -> str:
    """The DOC007-correct rewrite of a `frob:tests` target: keep the
    FIRST `::` (the file/qualname separator this graph's convention
    demands) intact, and replace every subsequent `::` (pytest's own
    `Class::method` collect-only separator) with a `.` -- turning
    `path::Class::method` into `path::Class.method`."""
    file_part, sep, rest = target.partition("::")
    return file_part + sep + rest.replace("::", ".")


def _origin_site(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin
    string -- a local copy of `frob.gates.__init__._site_from_edge_origin`
    (private to the package `__init__`, which imports this module, so
    importing back would cycle)."""
    file_part, sep, line_part = origin.rpartition(":")
    if sep and line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


def _rewrite_line_substring(path: Path, line: int, old: str, new: str) -> bool:
    """Replace the FIRST occurrence of `old` with `new` on 1-indexed
    `line` of `path`, in place. Returns whether a rewrite actually
    happened -- False (a no-op, never a partial/garbled write) if the
    file cannot be read, `line` is out of range, or `old` is not
    literally present on that line (the directive moved, or was already
    fixed by a prior run)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = text.splitlines(keepends=True)
    idx = line - 1
    if idx < 0 or idx >= len(lines):
        return False
    if old not in lines[idx]:
        return False
    lines[idx] = lines[idx].replace(old, new, 1)
    path.write_text("".join(lines), encoding="utf-8")
    return True


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_doc007_dotted_form(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix: rewrite every `frob:tests` directive whose target uses
    pytest's `Class::method` collect-only separator (DOC007) to this
    graph's own dotted `Class.method` form, in place, at its recorded
    origin site. A pure string rewrite -- semantics-preserving by
    construction, since the dotted form is definitionally what DOC007
    says the target SHOULD have been."""
    applied: list[FixApplied] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        if _DOUBLE_SEP_TESTS_TARGET_RE.search(edge.target) is None:
            continue
        file, line = _origin_site(edge.origin)
        fixed_target = _dotted_form(edge.target)
        if fixed_target == edge.target:
            continue
        if _rewrite_line_substring(root / file, line, edge.target, fixed_target):
            applied.append(
                FixApplied(
                    rule="DOC007",
                    file=file,
                    line=line,
                    detail=f"{edge.target!r} -> {fixed_target!r}",
                )
            )
    return applied


# ---------------------------------------------------------------------------
# DOC002: a `frob:doc` anchor slug that fuzzy-matches EXACTLY ONE real
# heading slug in its target doc.
# ---------------------------------------------------------------------------

#: Below this similarity ratio, a candidate is not a plausible typo/rename
#: of the original slug -- matches `_anchor_mismatch_message`'s own
#: `difflib.get_close_matches(slug, slugs, n=1, cutoff=0.0)` call's INTENT
#: (surface the nearest match for a human to read) but tightens the
#: cutoff for the auto-fix path specifically: a human reading a "did you
#: mean?" suggestion can reject a weak match on sight, an automated
#: rewrite cannot -- 0.6 is difflib's own conventional "close enough to
#: be the same thing, typo/rename shaped" threshold (its `get_close_
#: matches` default), not a value invented for this ticket.
_DOC002_FIX_CUTOFF = 0.6


def _doc002_unique_candidate(slug: str, slugs: set[str]) -> str | None:
    """The single fuzzy-match candidate slug for a mismatched DOC002
    `slug` against `slugs`, or `None` if there are zero or MORE THAN
    ONE candidates at `_DOC002_FIX_CUTOFF` or above -- an ambiguous or
    absent match is exactly the "stays unfixed with an assisted fix-it"
    case this ticket's acceptance criterion describes, never guessed."""
    # n=len(slugs): must see EVERY candidate above cutoff to tell "exactly
    # one" from "three or more" -- an n=2 cap would silently misreport a
    # genuinely 3-way-ambiguous slug as unique.
    candidates = difflib.get_close_matches(
        slug, slugs, n=len(slugs) or 1, cutoff=_DOC002_FIX_CUTOFF
    )
    if len(candidates) != 1:
        return None
    return candidates[0]


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_doc002_unique_slug(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix: for every `frob:doc`/`frob:tests` edge whose
    `<file>#<slug>` anchor target does not resolve (DOC002) but `slug`
    fuzzy-matches EXACTLY ONE real heading/`<a id>` slug in `<file>`
    (`_doc002_unique_candidate`), rewrite the directive's `#<slug>` in
    place to the matched candidate. Zero or multiple candidates are left
    entirely alone -- the assisted fix-it path (an unambiguous automated
    rewrite is never available there), per this ticket's own acceptance
    criterion.

    Calls back through `frob.gates._doclink_docanchor._doc_anchor_slugs`
    (lazy, call-time, same pattern the split gate modules already use)
    rather than importing at module load time, since `frob.gates.__init__`
    imports this module -- a top-level import back would cycle. T-1170
    moved `_doc_anchor_slugs` out of `gates/__init__.py` into
    `gates/_doclink_docanchor.py`; this import follows it to its new
    home rather than routing back through the parent package."""
    from frob.gates._doclink_docanchor import _doc_anchor_slugs

    applied: list[FixApplied] = []
    slug_cache: dict[str, set[str] | None] = {}
    for edge in snapshot.edges:
        if edge.kind not in (EdgeKind.DOC, EdgeKind.TESTS):
            continue
        target = edge.target
        if "#" not in target:
            continue
        docfile, _, slug = target.partition("#")
        if docfile not in slug_cache:
            resolved = _doc_anchor_slugs(root / docfile)
            slug_cache[docfile] = resolved.danger_some if resolved.is_some else None
        slugs = slug_cache[docfile]
        if slugs is None or slug in slugs:
            continue
        candidate = _doc002_unique_candidate(slug, slugs)
        if candidate is None:
            continue
        file, line = _origin_site(edge.origin)
        old_ref = f"{docfile}#{slug}"
        new_ref = f"{docfile}#{candidate}"
        if _rewrite_line_substring(root / file, line, old_ref, new_ref):
            applied.append(
                FixApplied(
                    rule="DOC002",
                    file=file,
                    line=line,
                    detail=f"{old_ref!r} -> {new_ref!r}",
                )
            )
    return applied


# ---------------------------------------------------------------------------
# INV006 (T-1177): auto-carry a split-carried waiver, Tier-A restricted to
# a VERBATIM-moved claim whose source already carries a covering
# `frob:waive INV006` (never an invariant bind -- that is a different
# obligation, out of this handler's "carry an EXISTING waiver" contract).
# ---------------------------------------------------------------------------


#: Per-suffix line-comment marker for the carried directive's inserted
#: line -- `find_carried_waiver`'s `fixit` text is the bare `frob:waive
#: ...` directive with no comment delimiter of its own (T-1134's message
#: suffix leaves that to the human reading the fix-it hint); this handler
#: writes an actually-parseable comment line, so it must supply one.
#: `INV006_SRC_SUFFIXES` is currently `(".py", ".rs")` -- both covered.
_INV006_LINE_COMMENT: dict[str, str] = {".py": "#", ".rs": "//"}


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_inv006_carried_waiver(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1177, T-1137 child): for every INV006 finding whose
    exclusivity-claim prose was moved VERBATIM out of a file that already
    carries a covering `frob:waive INV006`
    (`frob.gates._inv006_split_assist.find_carried_waiver`), insert that
    EXACT carried directive (a preset reference when the source itself
    used `preset=`, T-1176) as the new file's first line.

    This is not a new waiver in T-1137's never-auto-waive sense: the
    disposition was already made, explicitly, by a human, at the source
    site -- a module split moving the prose verbatim does not create a
    fresh judgment call, it just needs the SAME disposition to follow the
    text it was written for. Every other INV006 finding (no verbatim
    source match, or a match that only carries a bound `frob:invariant`
    rather than a waiver) is left untouched -- no guess, no waiver
    inserted, per this ticket's own acceptance criterion. Skips a file
    already carrying its own frob:waive/frob:invariant line 1 collision:
    `_rewrite_line_substring`'s sibling `_prepend_line` below simply never
    overwrites, it only ever inserts a new line 0, so this cannot corrupt
    an existing directive."""
    from frob.gates import INV006_SRC_DIRS, INV006_SRC_SUFFIXES

    applied: list[FixApplied] = []
    for src_dir in INV006_SRC_DIRS:
        src_root = root / src_dir
        if not src_root.is_dir():
            continue
        for suffix in INV006_SRC_SUFFIXES:
            for path in _iter_inv006_candidates(src_root, suffix):
                fix = _fix_inv006_carried_waiver_for_file(root, path, suffix, snapshot)
                if fix is not None:
                    applied.append(fix)
    return applied


def _fix_inv006_carried_waiver_for_file(
    root: Path, path: Path, suffix: str, snapshot: GraphSnapshot
) -> FixApplied | None:
    """`fix_inv006_carried_waiver`'s per-file body, split out to keep the
    caller's loop nest under ARCH001's function-length ceiling: the one
    INV006 carry (or `None`) for `path`, applying the rewrite in place
    when a covering waiver was found."""
    from frob.gates._inv006_split_assist import find_carried_waiver
    from frob.gates.invariants import find_exclusivity_claims

    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not find_exclusivity_claims(text):
        return None
    if _inv006_already_discharged(rel, snapshot):
        return None
    from frob.gates import INV006_SRC_DIRS, INV006_SRC_SUFFIXES

    carried = find_carried_waiver(
        root,
        text,
        exclude_rel=rel,
        candidate_dirs=INV006_SRC_DIRS,
        candidate_suffixes=INV006_SRC_SUFFIXES,
        snapshot=snapshot,
    )
    if carried is None:
        return None
    source_rel, kind, fixit = carried
    if kind != "waiver":
        return None  # an invariant bind is not a waiver to carry
    comment_line = _INV006_LINE_COMMENT.get(suffix, "#") + " " + fixit
    path.write_text(comment_line + "\n" + text, encoding="utf-8")
    return FixApplied(
        rule="INV006",
        file=rel,
        line=1,
        detail=f"carried {comment_line!r} from {source_rel}",
    )


def _iter_inv006_candidates(src_root: Path, suffix: str) -> list[Path]:
    """`frob.excludes.iter_files(src_root, suffix=suffix)`, materialized --
    a thin wrapper so `fix_inv006_carried_waiver` reads like the other
    Tier-A handlers' plain `for path in ...` loops."""
    from frob.excludes import iter_files

    return list(iter_files(src_root, suffix=suffix))


def _inv006_already_discharged(rel: str, snapshot: GraphSnapshot) -> bool:
    """True if `rel` already has a bound `frob:invariant` edge or a
    covering `frob:waive INV006` -- the same two ways
    `frob.gates._inv006_src_violations` treats INV006 as already
    discharged, duplicated narrowly here (rather than imported) since
    `frob.gates.__init__` imports this module, not the reverse."""
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.INVARIANT and edge.origin.rpartition(":")[0] == rel:
            return True
    for edge in snapshot.edges:
        if (
            edge.kind == EdgeKind.WAIVE
            and edge.target == "INV006"
            and (
                edge.origin.rpartition(":")[0] == rel
                or edge.src == rel
                or edge.src.startswith(f"{rel}::")
            )
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# TICK002: a T-draft-* provisional id that survived onto the default branch.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_tick002_renumber(root: Path, queue: TicketQueue) -> list[FixApplied]:
    """Tier-A fix: TICK002 already prescribes its own remedy in its
    message (`frob ticket renumber <draft-id> T-####`) -- this performs
    exactly that renumber for every draft id still in `queue` while
    `root` is on the default branch, via `finalize_draft` (T-0162's own
    finalize step, the same one `frob ticket land` calls -- no new
    renumber logic here, just invoking the existing API surface T-1138's
    own scope note anticipated). Includes T-1125's prose-reference
    rewrite automatically, since `finalize_draft` -> `renumber_one`
    already performs it. A no-op off the default branch (TICK002 itself
    never fires there either)."""
    from frob.gates import on_default_branch
    from frob.tickets._draft_finalize import finalize_draft

    applied: list[FixApplied] = []
    if not on_default_branch(root):
        return applied
    for tid in sorted(queue.tickets):
        if not is_draft_id(tid):
            continue
        result = finalize_draft(root, tid)
        if result.is_ok:
            applied.append(
                FixApplied(
                    rule="TICK002",
                    file="tickets.md",
                    line=0,
                    detail=f"{tid} -> {result.danger_ok}",
                )
            )
    return applied


# ---------------------------------------------------------------------------
# FMT001 (T-1261): a diff-touched `frob:` directive comment line over the
# project's configured line length -- `frob fmt` names itself as its own
# remedy.
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_fmt001_directive_wrap(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1261): FMT001 already names its own remedy verbatim
    (`run frob fmt <file>`) -- `format_paths` (`frob.gates._fmt_
    directives`, T-0441) is already idempotent, so calling it in write
    mode over `root` IS the fix; no new rewrite logic lives here.

    Runs over the whole `root`, not diff-scoped the way FMT001 itself is
    -- `format_paths` only ever rewrites a genuinely non-canonical
    `frob:` directive run; a line that is already canonical anywhere else
    in the tree is left byte-for-byte alone by construction, so widening
    the scope from "diff-touched" to "whole tree" cannot make an
    unrelated file worse, it only catches the SAME class of finding
    wherever it lives (`snapshot` is accepted for signature uniformity
    with its sibling Tier-A handlers; `format_paths` needs no graph
    state)."""
    from frob.gates._fmt_directives import format_paths, read_line_length

    del snapshot  # signature uniformity only, format_paths needs no graph state
    limit = read_line_length(root)
    report = format_paths(root, check_only=False, limit=limit)
    return [
        FixApplied(
            rule="FMT001",
            file=change.path,
            line=0,
            detail=f"{change.path}: frob: directive comment(s) rewrapped to canonical form",  # noqa: E501
        )
        for change in report.changes
    ]


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


def _mass_invalidation_rule(candidates: list[tuple[str, int, str]]) -> str | None:
    """The first target rule in `candidates` (each a `(file, line, rule)`
    WAIVE004 deletion candidate) whose count meets or exceeds
    `_WAIVE004_MASS_INVALIDATION_THRESHOLD`, or `None` if no rule does --
    the T-1323 incident's own shape (one rule family's waivers ALL going
    stale in the same run) treated as anomalous-zero-findings evidence in
    its own right, without needing a separately recorded baseline pool to
    compare against."""
    counts: dict[str, int] = {}
    for _file, _line, rule in candidates:
        counts[rule] = counts.get(rule, 0) + 1
    for rule, count in counts.items():
        if count >= _WAIVE004_MASS_INVALIDATION_THRESHOLD:
            return rule
    return None


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
    if idx < 0 or idx >= len(lines):
        return False
    if not _is_single_line_waiver(lines[idx], rule):
        return False
    del lines[idx]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def _waive004_verified_candidates(
    root: Path, gates: frozenset[str], ticket: str | None
) -> list[tuple[str, int, str]] | None:
    """`fix_waive004_stale_waiver`'s own self-manufactured `run_gates()`
    call, split out to keep the caller under ARCH001's function-length
    ceiling: `None` if the run errored, looked degraded
    (`_degraded_verification_reason`), or showed a mass-invalidation
    shape (`_mass_invalidation_rule`) -- any of the three means "delete
    nothing", per this handler's prove-fresh-or-do-nothing contract
    (T-1323). Otherwise the `(file, line, target_rule)` WAIVE004
    deletion candidates from a verified-trustworthy run."""
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

    mass_rule = _mass_invalidation_rule(candidates)
    if mass_rule is not None:
        _log.error(
            "WAIVE004 auto-fix: %d frob:waive %s directives went stale in one run "
            "(>= %d threshold) -- treating as a degraded/under-reporting run, "
            "deleting nothing",
            sum(1 for _f, _l, rule in candidates if rule == mass_rule),
            mass_rule,
            _WAIVE004_MASS_INVALIDATION_THRESHOLD,
        )
        return None

    return candidates


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
    that self-manufactured run for two structural degradation signals
    (`_degraded_verification_reason` -- stale/missing natives, any
    skipped gate stage) and, after collecting candidates, for a mass-
    invalidation shape (`_mass_invalidation_rule` -- one rule's waivers
    ALL going stale together in a single run, the 2026-07-29 incident's
    own signature). Either one aborts the ENTIRE batch -- zero waivers
    deleted, not a partial subset -- rather than acting on a verification
    run this handler cannot vouch for."""
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
# Public entry point
# ---------------------------------------------------------------------------

#: One rule id -> one Tier-A handler, uniform `(root, snapshot, queue) ->
#: list[FixApplied]` call shape (T-1261 promotes `apply_tier_a_fixes`'s
#: prior positional-call list to this explicit dict, keyed by rule id, per
#: docs/design/check-fix-engine.md's "Fix-handler protocol" section -- so
#: the fixability-registry-field ticket has a real table to introspect by
#: name). A handler whose OWN signature differs (three take `(root,
#: snapshot)`, one takes `(root, queue)`, `fix_waive004_stale_waiver` takes
#: extra keyword-only scope params) is adapted here via a thin lambda,
#: never by changing that handler's own signature -- T-1260's design-
#: review advisory noted this inconsistency and deferred the minimal fix
#: to this ticket; this dict IS that minimal fix, at the call-site layer
#: only. Order matters: DOC007/DOC002/INV006-carry/FMT001/REG010/REL002
#: are pure rewrites with no ledger interaction; TICK002 touches the
#: ticket ledger; WAIVE004 runs LAST since it re-invokes the whole gates
#: suite itself and should see every other handler's rewrites already
#: applied, not a stale pre-fix tree.
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
TIER_A_HANDLERS: dict[
    str, Callable[[Path, GraphSnapshot, TicketQueue], list[FixApplied]]
] = {
    "DOC007": lambda root, snapshot, queue: fix_doc007_dotted_form(root, snapshot),
    "DOC002": lambda root, snapshot, queue: fix_doc002_unique_slug(root, snapshot),
    "INV006": lambda root, snapshot, queue: fix_inv006_carried_waiver(root, snapshot),
    "FMT001": lambda root, snapshot, queue: fix_fmt001_directive_wrap(root, snapshot),
    "REG010": lambda root, snapshot, queue: fix_reg010_registry_sync(root, snapshot),
    "REL002": lambda root, snapshot, queue: fix_rel002_release_sync(root, snapshot),
    "TICK002": lambda root, snapshot, queue: fix_tick002_renumber(root, queue),
    "WAIVE004": lambda root, snapshot, queue: fix_waive004_stale_waiver(
        root, snapshot, queue
    ),
}


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_doc007_dotted_form_rewrite_applies_and_reverifies_clean kind="unit"  # noqa: E501
def apply_tier_a_fixes(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    exclude: tuple[str, ...] = (),
) -> list[FixApplied]:
    """Apply every Tier-A deterministic fix this batch ships (T-1138,
    T-1177, T-1261) via `TIER_A_HANDLERS`, in that dict's declared order
    (DOC007/DOC002/INV006-carry/FMT001/REG010/REL002 are pure rewrites
    with no ledger interaction; TICK002 touches the ledger; WAIVE004 runs
    last so it re-invokes the gates suite over every other handler's own
    rewrites already applied). Returns every fix actually made; inserts
    no NEW waiver, ever (INV006-carry only ever repeats an EXISTING human
    disposition at a verbatim-moved site, T-1177's coordinator-decision
    exception to the T-1137 never-auto-waive anti-goal; WAIVE004 only
    ever REMOVES a directive already proven dead by a fresh full run,
    never adds one), and skips (rather than guesses at) anything
    requiring judgment -- an ambiguous DOC002 candidate set or an
    already-correct DOC007 target is silently a no-op for that one
    finding, not an error."""
    applied: list[FixApplied] = []
    for rule_id, handler in TIER_A_HANDLERS.items():
        if rule_id in exclude:
            _log.info("tier-a fixes: %s excluded by caller", rule_id)
            continue
        applied.extend(handler(root, snapshot, queue))
    return applied
