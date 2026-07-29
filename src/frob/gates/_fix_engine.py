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
import re
from pathlib import Path

from pydantic import BaseModel

from frob.graph import EdgeKind, GraphSnapshot
from frob.tickets import TicketQueue
from frob.tickets._provisional import is_draft_id


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

    Calls back through `frob.gates._doc_anchor_slugs` (lazy, call-time,
    same pattern the split gate modules already use) rather than
    importing at module load time, since `frob.gates.__init__` imports
    this module -- a top-level import back would cycle."""
    from frob.gates import _doc_anchor_slugs

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
    from frob.tickets._new_renumber import finalize_draft

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
# Public entry point
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_doc007_dotted_form_rewrite_applies_and_reverifies_clean kind="unit"  # noqa: E501
def apply_tier_a_fixes(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> list[FixApplied]:
    """Apply every Tier-A deterministic fix this batch ships (T-1138):
    DOC007 dotted-form rewrite, DOC002 unique-anchor-slug correction,
    TICK002 draft renumber -- in that order (DOC007/DOC002 are pure
    source-text rewrites with no ledger interaction; TICK002 touches the
    ledger last so a source-text fix never races a concurrent renumber's
    own prose rewrite). Returns every fix actually made; inserts no
    waiver, ever, and skips (rather than guesses at) anything requiring
    judgment -- an ambiguous DOC002 candidate set or an already-correct
    DOC007 target is silently a no-op for that one finding, not an
    error."""
    applied: list[FixApplied] = []
    applied.extend(fix_doc007_dotted_form(root, snapshot))
    applied.extend(fix_doc002_unique_slug(root, snapshot))
    applied.extend(fix_tick002_renumber(root, queue))
    return applied
