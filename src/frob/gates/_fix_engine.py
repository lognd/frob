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
import fnmatch
import io
import json
import logging
import re
import tokenize
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from frob.graph import EdgeKind, GraphSnapshot
from frob.process._guard import guarded_subprocess_run
from frob.tickets import TicketQueue
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import atomic_write

if TYPE_CHECKING:
    from frob.gates import GateReport
    from frob.gates._suppress import SuppressionDialect

_log = logging.getLogger(__name__)


# frob:ticket T-1348
def _write_text(path: Path, text: str) -> bool:
    """Crash-safe replacement for a bare `path.write_text(...)` (T-1348):
    every Tier-A handler that rewrites a file IN PLACE routes through
    this instead, so a process killed mid-write (the T-1338 incident --
    `frob ticket land` timed out during its Tier-A auto-fix phase and
    left `src/frob/gates/_debt_deprecated.py` GARBLED, a half-applied
    rewrite) leaves the ORIGINAL file intact rather than truncated. Reuses
    `frob.tickets._store.atomic_write` (temp file + fsync + `os.replace`
    in the same directory, T-0456) rather than a second copy of the same
    primitive. Returns whether the write actually landed -- callers that
    unconditionally reported `True`/appended a `FixApplied` regardless of
    this outcome would silently claim a rewrite that never happened; logs
    and leaves the original untouched on the (should-never-happen) I/O
    failure path instead of raising, matching every other handler's "no
    rewrite is better than a bad one" posture."""
    result = atomic_write(path, text)
    if result.is_err:
        _log.error(
            "tier-a fixes: atomic write to %s failed, original left untouched: %s",
            path,
            result.danger_err,
        )
        return False
    return True


# frob:ticket T-1348
def _autofix_manifest_path(root: Path) -> Path:
    """Where `write_autofix_manifest`/`clear_autofix_manifest` (T-1348)
    keep the Tier-A auto-fix recovery breadcrumb -- `.frob/` already holds
    every other local, gitignored, cross-run scratch state this repo
    keeps (baseline, cache.db, leases), so a killed-mid-autofix manifest
    lives there rather than inventing a second convention."""
    return root / ".frob" / "land-autofix-manifest.json"


# frob:ticket T-1348
# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:tests tests/test_gates.py::TestAutofixManifest.test_write_then_clear_roundtrip
def write_autofix_manifest(root: Path, applied: list[FixApplied]) -> None:
    """Record `applied`'s distinct file paths, atomically, as the T-1348
    recovery breadcrumb naming every path `apply_tier_a_fixes` has
    rewritten SO FAR in the current run. `apply_tier_a_fixes` calls this
    after every handler completes, not just once at the end, so a process
    killed mid-loop (`frob ticket land`'s pre-land Tier-A phase, T-1175)
    leaves a manifest on disk that is accurate as of the last handler that
    finished -- a recovering agent diffs `git status` against this list
    instead of a blanket `git checkout --` that can silently discard its
    own uncommitted work in some OTHER file (the exact T-1338 incident).
    A no-op write when `applied` is empty still records "a pass started
    and touched nothing yet", which is itself useful signal; the file is
    only ever removed by `clear_autofix_manifest`, on a SUCCESSFUL finish."""
    paths = sorted({entry.file for entry in applied})
    manifest = {
        "rewritten_paths": paths,
        "fix_count": len(applied),
    }
    _write_text(_autofix_manifest_path(root), json.dumps(manifest, indent=2) + "\n")


# frob:ticket T-1348
# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:tests tests/test_gates.py::TestAutofixManifest.test_write_then_clear_roundtrip
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling; the documented breadcrumb-removal behavior is unchanged, so docs/modules/tickets.md#frob-ticket-land needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def clear_autofix_manifest(root: Path) -> None:
    """Remove the T-1348 recovery breadcrumb (`write_autofix_manifest`)
    after a Tier-A auto-fix pass finishes SUCCESSFULLY -- a completed pass
    needs no recovery guidance, its rewrites are now ordinary uncommitted
    changes like any other. A missing file is not an error (nothing to
    clear, e.g. a fresh worktree that never ran Tier-A fixes yet)."""
    path = _autofix_manifest_path(root)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # A permission/locking failure clearing the breadcrumb is not
        # this function's own contract to escalate (EXHAUST001, T-1371):
        # the manifest is a best-effort recovery aid, not load-bearing
        # state -- a leftover file after a successful pass is harmless.
        _log.debug("clear_autofix_manifest: could not remove %s", path)
    except Exception:
        _log.debug("clear_autofix_manifest: could not remove %s", path)


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
    try:
        if idx < 0 or idx >= len(lines):
            return False
        if old not in lines[idx]:
            return False
        lines[idx] = lines[idx].replace(old, new, 1)
    except (KeyError, IndexError, TypeError):
        # A directive's recorded `line` no longer lining up with the
        # file's current shape (edited concurrently, or a stale graph
        # snapshot) is exactly the "moved, do nothing" case this
        # function's own docstring already promises, not a crash
        # (EXHAUST001/EXHAUST002, T-1371).
        return False
    except Exception:
        return False
    return _write_text(path, "".join(lines))


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
    try:
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
    except Exception:
        # This handler's own contract (T-1323, `_waive004_verified_
        # candidates`'s sibling docstring) is "prove-fresh-or-do-nothing":
        # any surprise scanning/matching this one file means carry
        # nothing for it, never crash the whole Tier-A auto-fix pass over
        # every OTHER file (EXHAUST001/EXHAUST002, T-1371).
        return None
    if not _write_text(path, comment_line + "\n" + text):
        return None
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
#
# T-1391: `format_paths` being content-preserving everywhere it does NOT
# rewrite (a line already canonical anywhere else in the tree is left
# byte-for-byte alone by construction) does not make a whole-tree write
# SAFE from a land-scope-discipline standpoint -- a rewrite of a file
# outside a ticket's declared scope is still an out-of-scope WRITE, and
# land's own guards then reject the land that produced it (measured for
# real: `frob:waive` reason comments in an unrelated file mechanically
# rewritten by lands that never touched it, forcing one agent to widen
# its own ticket's scope record just to absorb the collateral edit).
# `fix_fmt001_directive_wrap`'s `only_paths` keyword restricts the
# rewrite to a caller-supplied set of `root`-relative paths instead of
# walking the whole tree; `only_paths=None` (the default) preserves the
# original whole-tree behaviour verbatim -- what a standalone `frob
# check --fix` still gets, and every existing caller until it opts in.
# This mirrors `fix_waive004_stale_waiver`'s `gates`/`ticket` keyword-
# only params below: a default-preserves-prior-behaviour scoping lever,
# testable directly with no change needed at any `TIER_A_HANDLERS`/
# `apply_tier_a_fixes` call site. Wiring a real caller (`frob ticket
# land`'s pre-land absorption step, `src/frob/app/ticket_runner/
# _land_cmd.py`, a different module) to actually pass its ticket's
# touched-file set through `only_paths` is tracked as a follow-up,
# outside this file's own scope.
# ---------------------------------------------------------------------------


def _fmt001_scoped_fixes(
    root: Path, limit: int, only_paths: frozenset[str]
) -> list[FixApplied]:
    """`fix_fmt001_directive_wrap`'s `only_paths` branch: format each
    named path individually (`format_paths` already accepts a single
    file as its `root` argument) instead of walking the whole tree. A
    named path that no longer exists (deleted since the caller's
    touched-set was computed) or is a directory is silently skipped,
    never an error -- the same no-guess Tier-A contract every other
    handler here follows. Reports `rel` (relative to the REAL repo
    `root`) rather than `format_paths`'s own per-call `change.path`,
    which would otherwise read as "." when called against a single
    file."""
    from frob.gates._fmt_directives import format_paths

    applied: list[FixApplied] = []
    for rel in sorted(only_paths):
        path = root / rel
        if not path.is_file():
            continue
        report = format_paths(path, check_only=False, limit=limit)
        applied.extend(
            FixApplied(
                rule="FMT001",
                file=rel,
                line=0,
                detail=f"{rel}: frob: directive comment(s) rewrapped to canonical form",  # noqa: E501
            )
            for _change in report.changes
        )
    return applied


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_fmt001_directive_wrap(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    only_paths: frozenset[str] | None = None,
) -> list[FixApplied]:
    """Tier-A fix (T-1261): FMT001 already names its own remedy verbatim
    (`run frob fmt <file>`) -- `format_paths` (`frob.gates._fmt_
    directives`, T-0441) is already idempotent, so calling it in write
    mode IS the fix; no new rewrite logic lives here. `only_paths`, when
    given, restricts the rewrite to exactly that set of `root`-relative
    paths (see `_fmt001_scoped_fixes`, and this section's own T-1391
    module comment above for the land-scope-discipline rationale);
    `None` (the default) preserves the original whole-tree behaviour.
    `snapshot` is accepted for signature uniformity with its sibling
    Tier-A handlers; `format_paths` needs no graph state."""
    from frob.gates._fmt_directives import format_paths, read_line_length

    del snapshot  # signature uniformity only, format_paths needs no graph state
    limit = read_line_length(root)
    if only_paths is not None:
        return _fmt001_scoped_fixes(root, limit, only_paths)
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
# SUPPRESS001 (T-1341, phase 2 of T-1339): write the reporting checker's
# own paired suppression, in this repo's observed canonical order, onto
# an evidence-driven dialect-mismatch line -- never a new judgment call,
# only the ONE rewrite `suppress001_gate` (`frob.gates._suppress`) already
# proves is correct: the reporting dialect's own rule code, verbatim.
# ---------------------------------------------------------------------------

#: This repo's own observed convention across every pre-existing dual-
#: dialect suppression line (confirmed by grep against the mypy-then-ty
#: paired-comment occurrences in src/tests at T-1341 authoring time):
#: mypy's ignore comment first, noqa second, ty's ignore comment last. A
#: line only ever carries the subset of these three it actually needs --
#: this order is the SLOT order, not a requirement that all three be
#: present.
_CANONICAL_DIALECT_ORDER = ("mypy", "ruff", "ty")

#: `suppress001_gate`'s own `Violation.message` shape (`_suppress001_
#: violation` in `frob.gates._suppress`): "... carries a {other_dialect}
#: suppression comment but {reporting_dialect} reports an unsuppressed
#: {code!r} diagnostic ...". Parsed back out rather than adding a
#: structured field to `Violation` just for this handler -- the same
#: precedent `_WAIVE004_TARGET_RULE_RE` above already sets for this
#: module.
_SUPPRESS001_MESSAGE_RE = re.compile(
    r"carries a \S+ suppression comment but (?P<reporting>\S+) reports an "
    r"unsuppressed (?P<code>'[^']*'|\"[^\"]*\") diagnostic"
)

#: A line carrying a `frob:` directive comment anywhere in its trailing
#: comment is `frob fmt`'s (FMT001's, `fix_fmt001_directive_wrap` above)
#: territory exclusively, never this handler's: FMT001 already prefers
#: backslash-continuation wrapping for an over-long directive, and its own
#: `canonicalize_text` already treats an existing trailing noqa pragma
#: (T-0985's own escape hatch) as deliberate and leaves it alone -- this
#: handler must never manufacture a competing suppression on a line
#: FMT001 also claims, or the two could double-fix or oscillate across
#: repeated `--fix` runs. Skipping any line matching this outright
#: (rather than trying to detect a genuine overlap) is the explicit
#: precedence this handler commits to: SUPPRESS001 never touches a
#: `frob:`-directive-bearing line, full stop.
_FROB_DIRECTIVE_MARKER_RE = re.compile(r"frob:")


def _parse_suppress001_message(message: str) -> tuple[str, str] | None:
    """The `(reporting_dialect, code)` pair a `suppress001_gate` finding's
    own message names, or `None` if the message does not match the
    expected shape (defensive; should not happen against this repo's own
    `_suppress001_violation`). The matched `code` group is always a
    Python `repr()` of a plain rule-code string (`_suppress001_violation`
    only ever formats `{code!r}` where `code` is a checker-reported rule
    id -- word characters and hyphens, never a quote character itself),
    so the surrounding quote characters are stripped directly rather than
    routed through `ast.literal_eval`/`eval` (an unnecessary opaque
    runtime-eval capability, per OPAQUE001, for input this simple and
    already regex-constrained to a quoted run with no embedded quote)."""
    match = _SUPPRESS001_MESSAGE_RE.search(message)
    if match is None:
        return None
    quoted = match.group("code")
    code = quoted[1:-1]
    return match.group("reporting"), code


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# tokenize.generate_tokens/io.StringIO, stdlib calls the resolver cannot statically \
# bound past the except (TokenError, IndentationError, SyntaxError, ValueError) below; \
# every documented raise path tokenize.generate_tokens can produce is already caught"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# tokenize's internal dict-keyed dispatch is conservatively assumed to leak KeyError; \
# no KeyError-raising call is reachable from this function's own source"
def _find_comment_start(line: str) -> int | None:
    """The column of the FIRST genuine trailing comment token on `line`
    (a single physical source line, no newline), or `None` if it carries
    no real comment -- tokenizes the DEDENTED line in isolation
    (`tokenize` correctly refuses to treat a `#` inside a string literal
    as a comment) and adds the stripped indentation back, so a line like
    `x = "a # b"` is never mistaken for carrying a trailing comment."""
    lstripped = line.lstrip()
    indent = len(line) - len(lstripped)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(lstripped + "\n").readline):
            if tok.type == tokenize.COMMENT:
                return indent + tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None
    return None


def _split_suppression_line(line: str) -> tuple[str, str, str]:
    """`line` split into `(code_part, comment_text, newline)`:
    `code_part` is everything before the first genuine trailing comment
    (`_find_comment_start`), rstripped; `comment_text` is that comment
    verbatim (empty if none); `newline` is the original line ending (`""`
    or `"\\n"`), preserved so the rewrite never changes it."""
    newline = "\n" if line.endswith("\n") else ""
    body = line[: len(line) - len(newline)] if newline else line
    comment_start = _find_comment_start(body)
    if comment_start is None:
        return body.rstrip(), "", newline
    return body[:comment_start].rstrip(), body[comment_start:], newline


def _merged_dialect_codes(
    present: dict[str, set[str] | None], dialect: str, code: str
) -> dict[str, set[str] | None]:
    """`present` (a line's existing per-dialect suppression codes, from
    `frob.gates._suppress._line_suppressions`) with `code` added under
    `dialect` -- idempotent (a no-op if `code` is already covered) and
    NEVER widens an existing bare suppression (`None`) to a coded one, per
    this ticket's own acceptance: a bare comment already covers every
    code, so leaving it bare is strictly more permissive, never less
    correct."""
    merged = dict(present)
    if dialect in merged:
        current = merged[dialect]
        if current is None or code in current:
            return merged
        merged[dialect] = current | {code}
    else:
        merged[dialect] = {code}
    return merged


def _format_dialect_segment(dialect: str, codes: set[str] | None) -> str:
    """The rendered `# ...` comment fragment for one dialect's `codes`
    (`None` renders bare, matching each dialect's own bare-suppression
    comment syntax) -- the inverse of `frob.gates._suppress._line_
    suppressions`' own per-dialect regexes."""
    joined = "" if codes is None else ",".join(sorted(codes))
    if dialect == "mypy":
        return "# type: ignore" if codes is None else f"# type: ignore[{joined}]"
    if dialect == "ty":
        return "# ty: ignore" if codes is None else f"# ty: ignore[{joined}]"
    return "# noqa" if codes is None else f"# noqa: {joined}"


def _strip_known_pragma_comments(
    comment_text: str, dialects: dict[str, SuppressionDialect]
) -> str:
    """`comment_text` with every recognized dialect pragma
    (`ty`/`mypy`/`ruff`'s own patterns) removed, leaving any OTHER
    trailing prose comment intact -- preserves a genuinely human-written
    explanatory comment sharing the line with a suppression, rather than
    discarding it when this handler rebuilds the pragma block."""
    remainder = comment_text
    for dialect in dialects.values():
        remainder = re.sub(dialect.pattern, "", remainder)
    return remainder.strip()


def _render_suppression_line(
    code_part: str,
    codes: dict[str, set[str] | None],
    leftover: str,
    newline: str,
) -> str:
    """Reassemble one source line from `code_part`, every dialect pragma
    in `codes` (rendered in `_CANONICAL_DIALECT_ORDER`), and any
    preserved `leftover` prose comment -- the single place this handler
    ever produces final line text, so canonical order/spacing is
    guaranteed uniform regardless of which dialect triggered the
    rewrite."""
    segments = [
        _format_dialect_segment(dialect, codes[dialect])
        for dialect in _CANONICAL_DIALECT_ORDER
        if dialect in codes
    ]
    pieces = [code_part, *segments]
    rendered = "  ".join(pieces)
    if leftover:
        rendered = f"{rendered}  {leftover}"
    return rendered + newline


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to dict.get chained \
# three deep and dict.items() iteration in the list-comprehension below, plain dict \
# operations the resolver cannot statically bound; the one real raise path \
# (tomllib.loads on malformed TOML) is caught above"
def _ruff_per_file_ignores(root: Path) -> list[tuple[str, set[str]]]:
    """`[tool.ruff.lint.per-file-ignores]` from `root/pyproject.toml`, as
    `(glob, codes)` pairs -- an empty list if the file/section is
    missing/unreadable (fail toward "nothing is pre-ignored", never
    toward silently over-suppressing)."""
    pyproject = root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    section = (
        data.get("tool", {}).get("ruff", {}).get("lint", {}).get("per-file-ignores", {})
    )
    if not isinstance(section, dict):
        return []
    return [
        (str(pattern), {str(c) for c in codes})
        for pattern, codes in section.items()
        if isinstance(codes, list)
    ]


def _code_ignored_for_path(root: Path, rel_path: str, code: str) -> bool:
    """True if ruff's own effective `per-file-ignores` configuration
    already silences `code` at `rel_path` -- adding a `# noqa: E501` there
    would be dead, no-op suppression noise (the T-1341 driver incident:
    2493 of 2623 `# noqa: E501` comments repo-wide sat under `tests/**`,
    where `E501` can never fire at all per this repo's own
    `pyproject.toml`). Prefix-matched (`code.startswith(ignored)`) so a
    broader category ignore (e.g. a bare `E5`) still covers `E501`,
    mirroring ruff's own rule-selector prefix semantics."""
    for pattern, codes in _ruff_per_file_ignores(root):
        if fnmatch.fnmatch(rel_path, pattern) and any(
            code.startswith(ignored) for ignored in codes
        ):
            return True
    return False


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# guarded_subprocess_run, a cross-module wrapper the resolver cannot see through; the \
# one documented raise path (FileNotFoundError, ruff binary missing) is caught below"
def _run_ruff_format(path: Path) -> None:
    """Best-effort `ruff format <path>` delegation -- the coordinator-
    directed fix for an over-long CODE line (a def/class signature):
    `ruff format` already wraps these correctly and completely (verified:
    it splits a >88-char `def` into one-parameter-per-line with a
    trailing comma), so this handler defers to it entirely rather than
    hand-rolling a signature wrapper that would duplicate the formatter
    (this repo's NO DUPLICATION rule) and be fought by the next `ruff
    format` run, which is authoritative for code layout. Errors are
    logged and swallowed -- a failed format attempt must not abort the
    whole SUPPRESS001 fix pass; the surviving-violation path below still
    applies a suppression if the line is still too long afterward."""
    try:
        result = guarded_subprocess_run(
            ["ruff", "format", str(path)], capture_output=True, text=True
        )
    except FileNotFoundError:
        _log.warning("SUPPRESS001 auto-fix: ruff binary not found, skipping format")
        return
    if result.is_err:
        _log.warning(
            "SUPPRESS001 auto-fix: ruff format on %s failed: %s",
            path,
            result.danger_err,
        )


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# _split_suppression_line/_line_suppressions_for_fix/_merged_dialect_codes/ \
# _strip_known_pragma_comments/_render_suppression_line/_code_ignored_for_path, \
# module-local helpers the resolver cannot see through; the one real raise path \
# (path.read_text) is caught above"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# _merged_dialect_codes indexes into `dialects` by `reporting`, a dict lookup the \
# resolver conservatively assumes can raise KeyError; `dialects` is always the full \
# SuppressionDialect registry passed in by the caller, and `reporting` is always a key \
# already validated against it upstream"
def _apply_one_suppress001_fix(
    root: Path,
    rel_file: str,
    line_no: int,
    reporting: str,
    code: str,
    dialects: dict[str, SuppressionDialect],
    limit: int,
) -> FixApplied | None:
    """The single-line rewrite for one SUPPRESS001 finding: append
    `reporting`'s own suppression for `code` in canonical order
    (`_render_suppression_line`), then -- only if the rewritten line now
    exceeds `limit` -- also add `# noqa: E501` UNLESS ruff's own
    `per-file-ignores` configuration already silences `E501` at this path
    (`_code_ignored_for_path`; adding one there would be dead-on-arrival
    noise, the T-1341 driver's own incident). Returns `None` (a no-op) if
    the file/line cannot be read, the line is `frob:`-directive-bearing
    (FMT001's territory, never this handler's), or the finding's own
    dialect/code is already covered (defensive; `suppress001_gate` should
    never emit that combination in the first place)."""
    path = root / rel_file
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines(keepends=True)
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return None
    original_line = lines[idx]
    code_part, comment_text, newline = _split_suppression_line(original_line)
    if _FROB_DIRECTIVE_MARKER_RE.search(comment_text):
        return None
    present = _line_suppressions_for_fix(comment_text, dialects)
    new_codes = _merged_dialect_codes(present, reporting, code)
    if new_codes == present:
        return None
    leftover = _strip_known_pragma_comments(comment_text, dialects)
    rendered = _render_suppression_line(code_part, new_codes, leftover, newline)

    noqa_added = False
    if "ruff" not in new_codes and len(rendered.rstrip("\n")) > limit:
        if not _code_ignored_for_path(root, rel_file, "E501"):
            new_codes = _merged_dialect_codes(new_codes, "ruff", "E501")
            rendered = _render_suppression_line(code_part, new_codes, leftover, newline)
            noqa_added = True

    if rendered == original_line:
        return None
    lines[idx] = rendered
    if not _write_text(path, "".join(lines)):
        return None
    detail = f"{original_line.rstrip(chr(10))!r} -> {rendered.rstrip(chr(10))!r}"
    if noqa_added:
        detail += " (+ noqa E501, line still over the configured limit after the fix)"
    return FixApplied(rule="SUPPRESS001", file=rel_file, line=line_no, detail=detail)


def _line_suppressions_for_fix(
    comment_text: str, dialects: dict[str, SuppressionDialect]
) -> dict[str, set[str] | None]:
    """`frob.gates._suppress._line_suppressions` applied to just
    `comment_text` (rather than a whole source line) -- a thin wrapper so
    an empty `comment_text` short-circuits to `{}` without a redundant
    regex pass."""
    from frob.gates._suppress import _line_suppressions

    if not comment_text:
        return {}
    return _line_suppressions(comment_text, dialects)


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_mypy_suppres\
# sed_ty_unsuppressed_gets_paired_suppression kind="unit"
# frob:tests \
# tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_idempotent_s\
# econd_fix_pass_is_a_no_op kind="unit"
def fix_suppress001_paired_suppression(
    root: Path, snapshot: GraphSnapshot
) -> list[FixApplied]:
    """Tier-A fix (T-1341, phase 2 of T-1339): for every SUPPRESS001
    finding, append the reporting checker's own suppression for its own
    reported rule code, in this repo's observed canonical order
    (`_CANONICAL_DIALECT_ORDER`) -- never a guessed code, never a
    cross-dialect code-mapping table (the exact static approach T-1339
    rejected), only the rule code the finding's own reporting oracle
    already supplied.

    Ordering (coordinator-directed, T-1341): `ruff format` is delegated to
    FIRST, for every file with a violation, before anything is written --
    an over-long CODE line (a def/class signature) belongs to the
    formatter (`_run_ruff_format`), never a hand-rolled wrapper. Only
    after that does this handler re-run `suppress001_gate` (line numbers
    may have shifted) and apply a suppression to whatever violation
    SURVIVES formatting; if a suppressed line is STILL over the limit
    afterward, `# noqa: E501` is added too, unless ruff's own
    `per-file-ignores` config already silences `E501` at that path
    (`_code_ignored_for_path` -- never write a no-op suppression).

    Idempotent by construction, not by bookkeeping: once a line carries
    both dialects' matching suppressions, the underlying diagnostic that
    `suppress001_gate` correlates against is itself silenced for both
    checkers, so a second `--fix` pass finds nothing left to fix on that
    line at all. Never touches a line carrying a `frob:` directive
    comment (FMT001's exclusive territory -- see
    `_FROB_DIRECTIVE_MARKER_RE`'s own docstring for the precedence
    rationale)."""
    from frob.gates._fmt_directives import read_line_length
    from frob.gates._suppress import suppress001_gate, suppression_dialects

    violations = suppress001_gate(root, snapshot)
    if not violations:
        return []

    for rel in sorted({v.file for v in violations}):
        _run_ruff_format(root / rel)

    violations = suppress001_gate(root, snapshot)
    if not violations:
        return []

    dialects = suppression_dialects()
    limit = read_line_length(root)
    applied: list[FixApplied] = []
    for violation in violations:
        parsed = _parse_suppress001_message(violation.message)
        if parsed is None:
            continue
        reporting, code = parsed
        fix = _apply_one_suppress001_fix(
            root, violation.file, violation.line, reporting, code, dialects, limit
        )
        if fix is not None:
            applied.append(fix)
    return applied


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
#: only. Order matters: DOC007/DOC002/INV006-carry/FMT001/SUPPRESS001/
#: REG010/REL002 are pure rewrites with no ledger interaction; TICK002
#: touches the ticket ledger; WAIVE004 runs LAST since it re-invokes the
#: whole gates suite itself and should see every other handler's
#: rewrites already applied, not a stale pre-fix tree. SUPPRESS001 runs
#: immediately AFTER FMT001, never before -- both can act on an
#: over-long line, and FMT001's directive-wrap gets first refusal
#: (T-1341: SUPPRESS001 never touches a `frob:`-directive-bearing line
#: at all, see `_FROB_DIRECTIVE_MARKER_RE`, so the two never actually
#: collide on the same physical line in practice -- the ordering is
#: still fixed explicitly rather than left to dict insertion accident).
#: SYS104/SYS100 (T-1531) are pure `.strata` text rewrites (same category
#: as DOC007/DOC002/INV006-carry/FMT001/REG010/REL002) reusing the
#: `frob.strata._sync_interface`/`frob.strata._sync_may` writers that
#: already back `frob sys sync-interface`; wiring them here (rather than
#: only the pre-land-only special-case call sites those writers already
#: had) is what makes the POST-land unscoped sweep (`_land_cmd.py::
#: _sweep_apply_tier_a_and_commit`) able to auto-repair them too.
# frob:ticket T-1531
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
TIER_A_HANDLERS: dict[
    str, Callable[[Path, GraphSnapshot, TicketQueue], list[FixApplied]]
] = {
    "DOC007": lambda root, snapshot, queue: fix_doc007_dotted_form(root, snapshot),
    "DOC002": lambda root, snapshot, queue: fix_doc002_unique_slug(root, snapshot),
    "INV006": lambda root, snapshot, queue: fix_inv006_carried_waiver(root, snapshot),
    "FMT001": lambda root, snapshot, queue: fix_fmt001_directive_wrap(root, snapshot),
    "SUPPRESS001": lambda root, snapshot, queue: fix_suppress001_paired_suppression(
        root, snapshot
    ),
    "REG010": lambda root, snapshot, queue: fix_reg010_registry_sync(root, snapshot),
    "REL002": lambda root, snapshot, queue: fix_rel002_release_sync(root, snapshot),
    "SYS104": lambda root, snapshot, queue: fix_sys104_interface_union(root, snapshot),
    "SYS100": lambda root, snapshot, queue: fix_sys100_may_via_union(root, snapshot),
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
    finding, not an error.

    T-1348: writes `write_autofix_manifest(root, applied)` (a recovery
    breadcrumb under `.frob/`, see its own docstring) after EVERY handler
    call, not just at the end -- if the CALLER (`frob ticket land`'s pre-
    land absorption step, T-1175) is killed partway through this loop, the
    manifest on disk still names every path a COMPLETED handler actually
    rewrote, so a recovering agent can tell "land's autofix touched this"
    from "this is my own uncommitted work" without a blanket `git checkout
    --`. Cleared (`clear_autofix_manifest`) once the whole loop finishes
    successfully, since a completed pass needs no recovery breadcrumb --
    its rewrites are now ordinary uncommitted changes like any other."""
    applied: list[FixApplied] = []
    for rule_id, handler in TIER_A_HANDLERS.items():
        if rule_id in exclude:
            _log.info("tier-a fixes: %s excluded by caller", rule_id)
            continue
        applied.extend(handler(root, snapshot, queue))
        write_autofix_manifest(root, applied)
    clear_autofix_manifest(root)
    return applied
