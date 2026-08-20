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

T-1646 (LARGE001 residue burndown) split the source-text/line-level
handler family (FMT001, SUPPRESS001, REG010, REL002, SYS100, E501,
COV002, WAIVE004) out to `frob.gates._fix_engine_text`, and the
common infra both families need (`FixApplied`, the manifest helpers) out
to `frob.gates._fix_engine_shared` (breaking what would otherwise be a
circular import between the two handler-family modules). This module
keeps the GRAPH-driven handlers (DOC007, DOC002, TICK002, TICK006) plus
`TIER_A_HANDLERS`/`apply_tier_a_fixes`, the dispatch table binding every
handler across all three files together; see the other two modules' own
docstrings for the seam this drew.

T-1763: the INV006 (split-carried-waiver) Tier-A handler that used to
live here was removed along with the rest of the INV006 gate -- see
`docs/modules/gates.md`'s T-1763 note for why (338 waivers, zero live
findings across the gate's whole lifetime, a purely lexical corpus-wide
keyword scan `frob:invariant`/INV001/INV002 already makes redundant)."""

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
from frob.gates._fix_engine_shared import (
    FixApplied,
    _write_text,
    clear_autofix_manifest,
    write_autofix_manifest,
)
from frob.gates._fix_engine_sync import (
    fix_cov002_ticket_directive_insertion,
    fix_docenum001_enumerates_sync,
    fix_reg010_registry_sync,
    fix_rel002_release_sync,
    fix_sys100_extended_whole_node_grant,
    fix_sys100_may_via_union,
    fix_sys111_capability_ratchet_sync,
    fix_waive004_stale_waiver,
)
from frob.gates._fix_engine_text import (
    fix_e501_merge_introduced,
    fix_fmt001_directive_wrap,
    fix_suppress001_paired_suppression,
)
from frob.gitio import run_argv
from frob.graph import EdgeKind, GraphSnapshot
from frob.tickets import Ticket, TicketQueue
from frob.tickets._provisional import is_draft_id

_log = logging.getLogger(__name__)


# frob:ticket T-2400
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_id_on_merge_target_but_not_workt\
# ree_is_silent kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_not_measured_merge_target_files_\
# nothing kind="unit"
class MergeTargetKnownIds(BaseModel):
    """Ticket ids resolvable on `frob ticket land`'s merge target (the
    primary checkout, i.e. main) at the moment the pre-land Tier-A batch
    runs -- BEFORE this land's own merge, so `ids` reflects whatever a
    sibling agent or the coordinator has filed on main in the meantime,
    not just this worktree's possibly-stale snapshot (T-2400).

    `measured=False` means the merge target's own active-ticket ledger
    (or, for the stricter posture this model exists to support, its
    archive) could not be loaded/parsed -- `fix_tick006_phantom_refile`
    treats that as NOT_MEASURED (doctrine T-2391: never conclude a
    citation is phantom from a view you could not fully read) and files
    nothing for this pass rather than risk a false-positive recovery
    ticket. `ids` is empty and meaningless whenever `measured` is
    `False`; callers must check `measured` first.

    T-2702: `root`, when given, is the merge target's own checkout path
    (main) -- `_tick006_try_resolve_without_filing`'s duplicate-recovery
    check reads it fresh, IN ADDITION to the caller's own (possibly
    stale) worktree `root`, closing the T-2699/T-2701 race: two lands in
    different worktrees, both citing the same phantom, where the SECOND
    land's own worktree ledger was cut before the FIRST land's recovery
    ticket existed on main. `ids` alone (a bare id set) cannot support
    this -- a title/scope duplicate check needs a real ledger to read,
    not just a membership set."""

    model_config = {}

    ids: frozenset[str] = frozenset()
    measured: bool = True
    root: Path | None = None


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
# TICK006: a phantom draft citation -- the id resolves to NO ticket at all,
# in either the active ledger or the archive, unlike TICK002's survived-
# draft case above.
# ---------------------------------------------------------------------------

#: How much of the phantom id's own claim window (see
#: `frob.gates._tickets_gate._TICK006_CLAIM_WINDOW`) to quote verbatim in
#: the refiled ticket's body -- generous enough to capture the whole
#: "Filed: T-draft-... (why)" sentence/paragraph without pulling in an
#: unrelated later claim.
_TICK006_CONTEXT_CHARS = 300


def _tick006_context_excerpt(done_report_text: str, tid: str) -> str:
    """The `_TICK006_CONTEXT_CHARS`-wide window of `done_report_text`
    centered on `tid`'s first occurrence -- the recoverable context a
    refiled ticket's body quotes verbatim, since the ORIGINAL claim
    (what the phantom id was supposed to cover) is the only description
    of the lost work that still exists anywhere. `""` if `tid` is
    somehow absent (defensive; every caller only ever passes an id
    `_tick006_phantom_ids` already found in this exact text)."""
    idx = done_report_text.find(tid)
    if idx == -1:
        return ""
    start = max(0, idx - _TICK006_CONTEXT_CHARS // 2)
    end = min(len(done_report_text), idx + _TICK006_CONTEXT_CHARS // 2)
    return done_report_text[start:end].strip()


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-1544
# frob:ticket T-2702
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_refiles_and_rewrites_citation \
# kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_known_id_is_never_touched \
# kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_two_lands_citing_same_draft_prod\
# uce_at_most_one_ticket kind="unit"
def fix_tick006_phantom_refile(
    root: Path,
    queue: TicketQueue,
    merge_target_ids: MergeTargetKnownIds | None = None,
    ticket_id: str | None = None,
) -> list[FixApplied]:
    """Tier-A fix: TICK006 (T-0726) flags a Done report's affirmative
    "filed" claim whose referenced id resolves to NO block anywhere --
    unlike TICK002 (a draft id that survived onto main and just needs
    `frob ticket renumber`), a TICK006 phantom was never real at all, so
    there is no existing ticket to rename FROM. This handler instead
    FILES the real ticket TICK006's own message tells the operator to
    file, then rewrites the phantom citation in the CLAIMING ticket's own
    body to the new real id -- the same whole-word prose-citation rewrite
    `renumber_one`/T-1125 already use for a real renumber
    (`_rewrite_body_prose_references`), reused rather than reimplemented
    here.

    The refiled ticket's body quotes the original claim's own surrounding
    text verbatim (`_tick006_context_excerpt`) -- the only surviving
    description of whatever work the phantom id was meant to cover, since
    the ticket itself never existed to describe it directly. Filed as
    `kind=bug`, `priority=high`: a phantom filing trail is itself the
    T-0707/T-0615 incident class TICK006 exists to catch, not ordinary
    follow-up work.

    A no-op whenever `new_ticket` itself fails (rare: worktree-lease
    violation, malformed evidence) -- the phantom citation is left
    exactly as TICK006 already reports it rather than silently rewritten
    to an id that was never actually filed, which would just create a
    SECOND phantom.

    T-2400: `root`/`queue` alone are `worktree`'s own pre-merge view --
    correct for a bare `frob check --fix` (no `merge_target_ids`, `None`
    default, byte-identical to pre-T-2400 behavior), but WRONG for `frob
    ticket land`'s pre-merge Tier-A pass, which used to resolve a
    citation's existence against this same stale view and file a
    spurious recovery ticket for an id a sibling agent or the
    coordinator had already filed on main after this worktree was cut
    (four occurrences in one day: T-2382/T-2383, T-2398/T-2399, T-2404,
    T-2439). `_tier_a_pre_land_step` now passes a `merge_target_ids`
    resolved from the land's actual merge target, unioned into
    `known_ids` here -- an id that exists on main but not yet in this
    worktree's own ledger is no longer phantom. `measured=False` (the
    merge target's own ledger could not be read) refuses to file
    ANYTHING this pass rather than risk exactly that false positive
    (doctrine T-2391) -- a genuinely phantom id just waits for the next
    land attempt, when the merge target is hopefully readable again.

    T-2690: three further false-positive/blast-radius fixes, all measured
    against a 92% false-positive rate (23/23 triaged auto-filings were
    bookkeeping duplicates of already-completed work, T-2690's own
    Measured section):

    1. `ticket_id`, when given (the landing ticket's id -- `None` for a
       bare `frob check --fix`, matching every other Tier-A handler's own
       T-1548 convention), scopes the whole scan to THAT ticket's own Done
       report alone, never the full active queue. Before this, a land's
       own pre-land Tier-A pass re-scanned EVERY ticket mirrored into the
       worktree's ledger (T-2563's ledger mirror puts the WHOLE fleet's
       active queue there) for phantom citations regardless of relevance
       to the ticket actually landing -- "a pre-land fixer for ticket A
       refuses the land of unrelated ticket B" was not a metaphor, it was
       this loop processing ticket B's own citation during ticket A's
       land.
    2. `_resolve_via_git_rename` is consulted for every candidate `tid`
       NOT already in `known_ids` before it is treated as phantom -- a
       draft id that survived only long enough to be renamed (`git mv`,
       what `frob ticket renumber`'s v2 path already does) to a real id
       is resolvable directly from git history, the actual "renumber map"
       this repo has, rather than re-derived from a snapshot of ids that
       necessarily cannot contain a rename's SOURCE name (the whole point
       of a rename is that the old name stops existing). This is the
       dominant false-positive shape T-2690 measured: a draft filed on a
       PARENT ticket's own worktree branch, cited from a SIBLING branch
       that copied the citation before the parent's land renumbered it,
       whose renumber the sibling's own worktree can never observe by
       ledger-snapshot comparison alone no matter how fresh (T-2400's own
       fix), only by asking git what happened to that exact path.
    3. `_tick006_refile_for_ticket` now checks `_find_exact_duplicate`
       (the SAME check `new_ticket`'s own `DuplicateTicket` refusal
       already performs, reused rather than reimplemented) BEFORE
       attempting to file -- a phantom citation already recovered by an
       earlier pass (the recovery ticket's own title is fully
       deterministic, see `_tick006_refile_ticket_spec`) has its citation
       rewritten to the EXISTING recovery ticket's id and stops there,
       instead of calling `new_ticket` again, hitting `DuplicateTicket`
       again, and leaving the SAME unrewritten phantom citation to repeat
       the identical failed attempt on every subsequent land -- the
       "refusing to file ... already has this exact title" noise a
       coordinator misdiagnosed as lock contention for 45 minutes,
       because retrying a duplicate-title refusal, unlike contention,
       never clears on its own."""
    from frob.tickets._store import load_archive

    if merge_target_ids is not None and not merge_target_ids.measured:
        _log.warning(
            "fix_tick006_phantom_refile: NOT_MEASURED -- the land merge "
            "target's ticket ledger could not be read; skipping all "
            "phantom-citation filing this pass rather than risk a false "
            "positive (T-2400)"
        )
        return []
    archived = load_archive(root)
    known_ids = set(queue.tickets) | (
        set(archived.danger_ok) if archived.is_ok else set()
    )
    if merge_target_ids is not None:
        known_ids |= merge_target_ids.ids
    if ticket_id is not None:
        scoped_ticket = queue.tickets.get(ticket_id)
        tickets_to_scan = [scoped_ticket] if scoped_ticket is not None else []
    else:
        tickets_to_scan = sorted(queue.tickets.values(), key=lambda t: t.id)
    applied: list[FixApplied] = []
    for ticket in tickets_to_scan:
        applied.extend(
            _tick006_refile_for_ticket(root, ticket, known_ids, merge_target_ids)
        )
    return applied


#: How long to wait on any single git spawn `_resolve_via_git_rename`
#: makes -- bounded and small: this runs once per candidate phantom id
#: (rare), never in a hot loop, but must never hang a land on a slow/
#: huge-history git spawn.
_TICK006_GIT_RENAME_TIMEOUT_S = 10.0


def _resolve_via_git_rename(root: Path, tid: str) -> str | None:
    """Back-compat wrapper over `_resolve_via_git_rename_measured` for any
    caller that only needs the resolved id, not whether the lookup was
    fully measured -- see that function's docstring for the T-2702 fix
    this split exists to support. Discards the measured flag, so ONLY use
    this where an unmeasured git spawn being silently treated as "no
    rename" is acceptable; `_tick006_try_resolve_without_filing` uses the
    measured variant directly instead, precisely because it is not."""
    resolved, _measured = _resolve_via_git_rename_measured(root, tid)
    return resolved


# frob:ticket T-2702
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_git_rename_lookup_failure_files_\
# nothing_never_treated_as_confirmed_non_rename kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_lookup_failure_then_clean_retry_\
# recovers_correctly kind="unit"
def _resolve_via_git_rename_measured(root: Path, tid: str) -> tuple[str | None, bool]:
    """T-2690: best-effort resolution of `tid` (an id TICK006's own
    ledger-snapshot lookup could not find) via git's OWN rename record --
    the real "renumber map" this repo has, since `frob ticket renumber`'s
    v2 path (`renumber_one_v2`) does a `git mv` of `tickets/<old>/` to
    `tickets/<new>/`, and a ledger snapshot (active+archive+merge-target,
    all consulted before this is ever called) structurally cannot contain
    a rename's SOURCE name -- the whole point of a rename is that the old
    name stops existing anywhere a snapshot could see it.

    T-2702: returns `(resolved_id, measured)` -- T-2690's original single
    `str | None` return collapsed "no rename exists" and "a git spawn
    failed/timed out" into the identical `None`, which its OWN docstring
    defended as deliberate ("exactly like a genuinely nonexistent id").
    That is precisely backwards, and directly contradicts this same
    module's T-2391 doctrine everywhere else (`merge_target_ids.
    measured=False` refuses to file rather than risk a false positive):
    under real concurrent-land git contention (measured: this repo's own
    incident, T-2699/T-2701, both landed on top of a working fix, both
    during a multi-agent drive with background auto-gc packing on every
    commit) a `_TICK006_GIT_RENAME_TIMEOUT_S`-bounded spawn CAN and DID
    time out, and the caller filed a duplicate phantom-recovery ticket
    for an id that a fresh, unloaded git spawn resolves correctly in
    under a second. `measured=True` means every git spawn this lookup
    needed completed (exit 0) -- `resolved_id` is then trustworthy either
    way (a real successor id, or genuinely `None` because no `R` line
    named this path). `measured=False` means SOME spawn failed, timed
    out, or exited nonzero -- `resolved_id` is always `None` in that case
    and must NOT be treated as "confirmed not a rename"; the caller
    should treat this exactly like `MergeTargetKnownIds.measured=False`
    and file nothing this pass rather than risk the exact false positive
    this incident measured.

    Two-step lookup: (1) `git log --all --diff-filter=D -- tickets/<tid>/
    ticket.md` finds every commit where this old path was REMOVED (a
    rename's deletion half is visible to a pathspec-filtered log even
    though the paired addition is not, since rename-PAIRING requires
    both sides in the same diff and pathspec-filtering drops the new
    side); (2) for each such commit, `git show -M --name-status`
    (unrestricted, so both sides of the pair are present) is checked for
    an `R<NNN>` line whose source is exactly this old path -- if found,
    its destination's own `tickets/<new-id>/...` prefix is the resolved
    successor id. Multiple candidate commits are tried oldest-relevant-
    first-found; a `tid` that was genuinely deleted (not renamed)
    matches no `R` line in any of them and this returns `(None, True)` --
    a clean, fully-measured miss, distinct from `(None, False)`."""
    from frob.gitio import run_argv

    old_path = f"tickets/{tid}/ticket.md"
    log_result = run_argv(
        ["git", "log", "--all", "--diff-filter=D", "--format=%H", "--", old_path],
        cwd=root,
        timeout_s=_TICK006_GIT_RENAME_TIMEOUT_S,
    )
    if log_result.is_err:
        _log.warning(
            "_resolve_via_git_rename_measured: git log spawn failed for "
            "%s -- UNMEASURED, not a confirmed non-rename (T-2702)",
            tid,
        )
        return None, False
    if log_result.danger_ok.returncode != 0:
        _log.warning(
            "_resolve_via_git_rename_measured: git log exited %d for %s "
            "-- UNMEASURED, not a confirmed non-rename (T-2702)",
            log_result.danger_ok.returncode,
            tid,
        )
        return None, False
    commit_shas = log_result.danger_ok.stdout.split()
    for commit_sha in commit_shas:
        resolved, candidate_measured = _tick006_check_rename_candidate(
            root, commit_sha, old_path, tid
        )
        if not candidate_measured:
            return None, False
        if resolved is not None:
            return resolved, True
    return None, True


# frob:ticket T-2702
def _tick006_check_rename_candidate(
    root: Path, commit_sha: str, old_path: str, tid: str
) -> tuple[str | None, bool]:
    """One candidate commit's own share of `_resolve_via_git_rename_
    measured`'s scan -- split out purely to keep that function under
    ARCH001's line threshold, no behavior change. Returns `(resolved_id,
    measured)`: `measured=False` (a `git show` spawn failed/timed out)
    must short-circuit the caller's whole scan as UNMEASURED, same
    T-2391 doctrine as the rest of this module -- a partial scan across
    candidates is not the same as "checked every candidate, found
    nothing"."""
    from frob.gitio import run_argv

    show_result = run_argv(
        ["git", "show", "-M", "--name-status", "--format=", commit_sha],
        cwd=root,
        timeout_s=_TICK006_GIT_RENAME_TIMEOUT_S,
    )
    if show_result.is_err or show_result.danger_ok.returncode != 0:
        _log.warning(
            "_resolve_via_git_rename_measured: git show spawn failed "
            "for candidate %s (tid=%s) -- UNMEASURED, not a confirmed "
            "non-rename (T-2702)",
            commit_sha,
            tid,
        )
        return None, False
    for line in show_result.danger_ok.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].startswith("R"):
            continue
        status, src, dst = parts
        if src != old_path:
            continue
        dst_parts = dst.split("/")
        if len(dst_parts) >= 2 and dst_parts[0] == "tickets":
            return dst_parts[1], True
    return None, True


def _tick006_refile_ticket_spec(ticket: Ticket, tid: str, excerpt: str):  # noqa: ANN201
    """The `TicketSpec` for the real ticket refiled in place of phantom
    `tid` (cited by `ticket`), quoting `excerpt` (the original claim's own
    surrounding text) verbatim -- split out of `_tick006_refile_for_ticket`
    purely to keep that function under ARCH001's line threshold, no
    behavior change."""
    from frob.tickets import Origin, Priority, TicketKind, TicketSpec

    return TicketSpec(
        title=f"Recovered from {ticket.id}'s phantom TICK006 citation of {tid}",
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        body=(
            f"Auto-filed by the TICK006 Tier-A fix (T-1544): "
            f"{ticket.id}'s Done report claimed {tid} was filed, but "
            f"{tid} resolves to no block in tickets.md or "
            f"tickets-archive.md -- a phantom filing trail. The original "
            f"claim's own surrounding text (the only surviving "
            f"description of the intended work) is quoted verbatim "
            f"below; review and refine as needed.\n\n> {excerpt}"
        ),
    )


def _tick006_rewrite_citation(
    current_body: str, tid: str, resolved_id: str, ticket_id: str, reason: str
) -> tuple[str, FixApplied | None]:
    """T-2690: the shared "citation resolved WITHOUT filing" rewrite both
    `_resolve_via_git_rename` hits and `_find_exact_duplicate` hits use --
    split out purely to keep `_tick006_refile_for_ticket` under ARCH001's
    line threshold, no behavior change. Returns the (possibly rewritten)
    body plus a `FixApplied` when the rewrite actually hit something, or
    `None` when `_rewrite_body_prose_references` found nothing to touch
    (defensive; `tid` was just found IN this body, so this should not
    happen in practice)."""
    from frob.tickets._new_renumber import _rewrite_body_prose_references

    new_body, hits = _rewrite_body_prose_references(current_body, {tid: resolved_id})
    if not hits:
        return new_body, None
    return new_body, FixApplied(
        rule="TICK006",
        file="tickets.md",
        line=0,
        detail=f"{tid} -> {resolved_id} ({reason}, cited by {ticket_id}, not refiled)",
    )


def _tick006_try_resolve_without_filing(
    root: Path,
    tid: str,
    ticket: Ticket,
    current_body: str,
    known_ids: set[str],
    done_report_text: str,
    merge_target_ids: "MergeTargetKnownIds | None" = None,
) -> tuple[str, FixApplied | None, bool]:
    """T-2690/T-2702: the checks `_tick006_refile_for_ticket` runs BEFORE
    ever calling `new_ticket` -- a genuine git rename
    (`_resolve_via_git_rename_measured`), an already-filed recovery
    ticket found against THIS worktree's own ledger, or (T-2702) the
    SAME duplicate check re-run against the land's actual merge target
    when one is known. Returns `(body, applied, resolved)` --
    `resolved=True` short-circuits the caller's loop iteration (citation
    already rewritten, or deliberately left untouched pending better
    information -- nothing left to file this pass); `False` means `tid`
    survived every check and genuinely needs `new_ticket`.

    T-2702: `_resolve_via_git_rename_measured`'s `measured=False` (a git
    spawn failed/timed out, e.g. under the exact concurrent-land
    contention T-2699/T-2701 measured) now REFUSES to file anything for
    `tid` this pass -- `resolved=True` with no citation rewrite, mirroring
    `fix_tick006_phantom_refile`'s own top-level `merge_target_ids.
    measured=False` doctrine (T-2391: never conclude "not a rename" from
    an incomplete git view). A `tid` that keeps hitting this either
    resolves on a later, less-contended pass, or genuinely needs a human
    to look -- either is safe; a spurious duplicate recovery ticket is
    not.

    T-2702: `_find_exact_duplicate` is now ALSO checked against
    `merge_target_ids.root` (the land's actual merge target, i.e. main,
    read fresh every call) when that differs from `root` -- this
    worktree's own `root` can be a stale ledger mirror cut before a
    SIBLING land (running concurrently, in a different worktree) filed
    the exact same byte-identical recovery ticket seconds-to-minutes
    earlier; T-2699/T-2701 are exactly this shape (T-2141's land filed
    T-2699, T-2251's land filed a byte-identical duplicate T-2701 because
    its own worktree's ledger snapshot predated T-2699). Checking BOTH
    views closes that race without weakening `_find_exact_duplicate`'s
    own exact-title/exact-scope precision -- it is the same function,
    called against two roots, first hit wins."""
    from frob.tickets._new_renumber import _find_exact_duplicate

    renamed_to, rename_measured = _resolve_via_git_rename_measured(root, tid)
    if renamed_to is not None:
        known_ids.add(renamed_to)
        body, applied = _tick006_rewrite_citation(
            current_body, tid, renamed_to, ticket.id, "resolved via git rename"
        )
        return body, applied, True
    if not rename_measured:
        _log.warning(
            "fix_tick006_phantom_refile: %s (cited by %s) UNMEASURED via "
            "git rename lookup -- skipping this pass rather than risk a "
            "false-positive recovery ticket (T-2702)",
            tid,
            ticket.id,
        )
        return current_body, None, True

    excerpt = _tick006_context_excerpt(done_report_text, tid)
    spec = _tick006_refile_ticket_spec(ticket, tid, excerpt)
    existing = _find_exact_duplicate(root, spec)
    merge_target_root = (
        merge_target_ids.root if merge_target_ids is not None else None
    )
    if existing is None and merge_target_root is not None and merge_target_root != root:
        existing = _find_exact_duplicate(merge_target_root, spec)
    if existing is not None:
        known_ids.add(existing.id)
        body, applied = _tick006_rewrite_citation(
            current_body,
            tid,
            existing.id,
            ticket.id,
            "already recovered by an earlier pass",
        )
        return body, applied, True

    return current_body, None, False


def _tick006_file_new_recovery_ticket(
    root: Path,
    tid: str,
    ticket: Ticket,
    current_body: str,
    known_ids: set[str],
    done_report_text: str,
) -> tuple[str, FixApplied | None]:
    """T-2690: the actual `new_ticket` call for a `tid` that survived
    both `_tick006_try_resolve_without_filing` checks -- split out purely
    to keep `_tick006_refile_for_ticket` under ARCH001's line threshold,
    no behavior change from the pre-T-2690 shape. A no-op (returns the
    body unchanged, `None`) whenever `new_ticket` itself fails, matching
    this handler's pre-existing contract: the phantom citation is left
    exactly as TICK006 reports it rather than rewritten to an id that
    was never actually filed."""
    from frob.tickets import new_ticket
    from frob.tickets._new_renumber import _rewrite_body_prose_references

    excerpt = _tick006_context_excerpt(done_report_text, tid)
    spec = _tick006_refile_ticket_spec(ticket, tid, excerpt)
    created = new_ticket(root, spec)
    if created.is_err:
        _log.warning(
            "fix_tick006_phantom_refile: could not refile %s (cited by %s): %s",
            tid,
            ticket.id,
            created.danger_err,
        )
        return current_body, None
    new_id = created.danger_ok.id
    known_ids.add(new_id)
    new_body, hits = _rewrite_body_prose_references(current_body, {tid: new_id})
    if not hits:
        return new_body, None
    return new_body, FixApplied(
        rule="TICK006",
        file="tickets.md",
        line=0,
        detail=f"{tid} -> {new_id} (refiled, cited by {ticket.id})",
    )


def _tick006_refile_for_ticket(
    root: Path,
    ticket: Ticket,
    known_ids: set[str],
    merge_target_ids: "MergeTargetKnownIds | None" = None,
) -> list[FixApplied]:
    """One ticket's own share of `fix_tick006_phantom_refile`'s work:
    scan its Done report for phantom citations, refile a real ticket for
    each, and rewrite them in place -- split out of the parent purely to
    keep it under ARCH001's line threshold. Mutates `known_ids` in place
    (adds each newly refiled id) so a LATER ticket in the same pass never
    double-files against an id THIS pass already claimed.

    T-2690/T-2702: a candidate `tid` is resolved further ways
    (`_tick006_try_resolve_without_filing`) before ANY `new_ticket` call
    is attempted -- via a MEASURED git rename lookup (a genuine renumber,
    citation rewritten to the real successor id, never filed; an
    UNMEASURED lookup also never files, T-2702) and via
    `_find_exact_duplicate` checked against both this worktree's own
    ledger AND (T-2702) the land's actual merge target, when known (an
    earlier pass -- possibly a concurrently-running SIBLING land -- has
    already recovered this exact phantom, citation rewritten to the
    EXISTING recovery ticket, never refiled a second time). Only a `tid`
    that survives every check reaches `new_ticket` at all."""
    from frob.gates._tickets_gate import _tick006_done_report_text, _tick006_phantom_ids
    from frob.tickets._store import write_ticket

    done_report_text = _tick006_done_report_text(ticket.body)
    if not done_report_text:
        return []
    applied: list[FixApplied] = []
    current_body = ticket.body
    for tid in _tick006_phantom_ids(done_report_text):
        if tid in known_ids:
            continue
        current_body, resolved_fix, resolved = _tick006_try_resolve_without_filing(
            root,
            tid,
            ticket,
            current_body,
            known_ids,
            done_report_text,
            merge_target_ids,
        )
        if resolved_fix is not None:
            applied.append(resolved_fix)
        if resolved:
            continue
        current_body, filed_fix = _tick006_file_new_recovery_ticket(
            root, tid, ticket, current_body, known_ids, done_report_text
        )
        if filed_fix is not None:
            applied.append(filed_fix)
    if current_body != ticket.body:
        write_ticket(root, ticket.model_copy(update={"body": current_body}))
    return applied


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


# frob:ticket T-1545
# frob:ticket T-1924
def _fix_sys100_both_cases(root: Path) -> list[FixApplied]:
    """SYS100 has two disjoint fixers (T-1531 CORE, T-1545 EXTENDED) that
    both resolve findings under the same rule id -- run both and
    concatenate rather than let a dict literal's single `"SYS100"` key
    silently drop one. `fix_sys100_may_via_union` runs first (its
    per-file `via` widen is the more targeted fix; running it before the
    whole-node EXTENDED insertion means a file that already tripped a
    CORE widening this same pass does not also need a broader EXTENDED
    grant re-derived against stale text). T-1924: both callees dropped
    their unused `snapshot` parameter, so this wrapper no longer takes
    or forwards one either."""
    return [
        *fix_sys100_may_via_union(root),
        *fix_sys100_extended_whole_node_grant(root),
    ]


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
#: REG010/REL002/DOCENUM001 are pure rewrites with no ledger interaction; TICK002
#: touches the ticket ledger; WAIVE004 runs LAST since it re-invokes the
#: whole gates suite itself and should see every other handler's
#: rewrites already applied, not a stale pre-fix tree. SUPPRESS001 runs
#: immediately AFTER FMT001, never before -- both can act on an
#: over-long line, and FMT001's directive-wrap gets first refusal
#: (T-1341: SUPPRESS001 never touches a `frob:`-directive-bearing line
#: at all, see `_FROB_DIRECTIVE_MARKER_RE`, so the two never actually
#: collide on the same physical line in practice -- the ordering is
#: still fixed explicitly rather than left to dict insertion accident).
#: SYS100 (T-1531) is a pure `.strata` text rewrite (same category as
#: DOC007/DOC002/INV006-carry/FMT001/REG010/REL002) reusing the
#: `frob.strata._sync_may` writer; wiring it here (rather than only a
#: pre-land-only special-case call site) is what makes the POST-land
#: unscoped sweep (`_land_cmd.py::_sweep_apply_tier_a_and_commit`) able
#: to auto-repair it too. T-1870: SYS104 (the `interface=` sibling of
#: this same category) is deliberately NOT wired here any more -- deleted
#: entirely, along with its writer and every other `interface=` mutation
#: path, per an explicit owner directive that no code path may
#: auto-update declared public-symbol surface. T-1872 wired a
#: `SYS-IFACE-ORDER` entry here too (declared-name presentation reorder
#: only, no membership decision); T-1916 removed it again -- REG002 found
#: no gate/policy rule of that id had ever existed to justify the
#: registry's "live, enforced gate rule" claim about it, and every OTHER
#: entry in this dict is backed by a real detector somewhere. See
#: `_fix_engine_sync.py`'s own module docstring for the retirement
#: reasoning in full.
# frob:ticket T-1531
# frob:ticket T-1924
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
#: T-1548: every handler now takes a 4th `ticket_id: str | None` argument
#: (the landing ticket's id, when `apply_tier_a_fixes` is called from a
#: land context -- `None` for a bare `frob check --fix`) -- every existing
#: handler simply ignores it, only `fix_cov002_ticket_directive_insertion`
#: reads it, since inserting a `frob:ticket <id>` directive is the one
#: Tier-A fix that structurally needs to know WHICH ticket is landing
#: (there is no other way to derive that from `root`/`snapshot`/`queue`
#: alone -- multiple tickets can be simultaneously open).
#: T-2400: every handler now ALSO takes a 5th `merge_target_ids:
#: MergeTargetKnownIds | None` argument, same uniform-shape precedent as
#: T-1548's `ticket_id` -- `None` for a bare `frob check --fix` (no land
#: merge target to resolve). Only `fix_tick006_phantom_refile` reads it,
#: for the identical reason `ticket_id` above is read by only one
#: handler: resolving a phantom citation against the land's actual merge
#: target, not just this worktree's own stale ledger view.
TIER_A_HANDLERS: dict[
    str,
    Callable[
        [Path, GraphSnapshot, TicketQueue, "str | None", "MergeTargetKnownIds | None"],
        list[FixApplied],
    ],
] = {
    "DOC007": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_doc007_dotted_form(root, snapshot)
    ),
    "DOC002": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_doc002_unique_slug(root, snapshot)
    ),
    "FMT001": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_fmt001_directive_wrap(root)
    ),
    "SUPPRESS001": (
        lambda root, snapshot, queue, ticket_id, merge_target_ids: (
            fix_suppress001_paired_suppression(root, snapshot)
        )
    ),
    "REG010": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_reg010_registry_sync(root)
    ),
    "DOCENUM001": (
        lambda root, snapshot, queue, ticket_id, merge_target_ids: (
            fix_docenum001_enumerates_sync(root, snapshot)
        )
    ),
    "REL002": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_rel002_release_sync(root)
    ),
    "SYS100": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        _fix_sys100_both_cases(root)
    ),
    # frob:ticket T-2001
    # Runs immediately after SYS100 (dict order, `apply_tier_a_fixes`'
    # own docstring): the ratchet-sync handler's BEFORE-vs-CURRENT
    # attribution depends on SYS100's own via-list widening already
    # having happened on disk in THIS SAME pass.
    "SYS111": (
        lambda root, snapshot, queue, ticket_id, merge_target_ids: (
            fix_sys111_capability_ratchet_sync(root)
        )
    ),
    "E501": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_e501_merge_introduced(root)
    ),
    "COV002": (
        lambda root, snapshot, queue, ticket_id, merge_target_ids: (
            fix_cov002_ticket_directive_insertion(root, snapshot, queue, ticket_id)
        )
    ),
    "TICK002": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_tick002_renumber(root, queue)
    ),
    "TICK006": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_tick006_phantom_refile(root, queue, merge_target_ids, ticket_id)
    ),
    "WAIVE004": lambda root, snapshot, queue, ticket_id, merge_target_ids: (
        fix_waive004_stale_waiver(root, snapshot, queue)
    ),
}


# frob:ticket T-2351
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_pre_fix_dirty_snapshot_captures_uncommitted_content kind="unit"  # noqa: E501
def _snapshot_dirty_files(root: Path) -> dict[str, bytes]:
    """The exact on-disk bytes, right now, of every file `git status`
    already shows as uncommitted-dirty (modified, staged, or both) in
    `root` -- `apply_tier_a_fixes`'s own T-2351 fix calls this ONCE,
    before its handler loop runs any Tier-A rewrite, so a later
    disqualified fix can be undone back to the CALLER's own pre-handler
    state (`_fix_engine_scope._revert_fix_file`) instead of `HEAD`. Never
    raises: a `git status`/read failure degrades to `{}` (the pre-T-2351
    `git checkout --`-to-HEAD fallback then applies unchanged, matching
    behavior for a repo this call cannot introspect). Untracked files are
    deliberately excluded (`--porcelain`'s `??` entries) -- a Tier-A
    handler acts only on TRACKED source files, so an untracked file can
    never be the thing this snapshot needs to protect."""
    result = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if result.is_err or result.danger_ok.returncode != 0:
        _log.warning(
            "tier-a fixes: pre-fix dirty snapshot: could not read git "
            "status -- disqualified fixes will fall back to HEAD-restore"
        )
        return {}
    snapshot: dict[str, bytes] = {}
    for line in result.danger_ok.stdout.splitlines():
        if not line or line.startswith("??"):
            continue
        # porcelain v1: "XY <path>" (a rename entry's "old -> new" is
        # deliberately not split further -- renames are rare for a
        # source file mid-ticket and the new path's own status line, if
        # dirty, is picked up on the next iteration same as any other).
        rel_path = line[3:].strip()
        if not rel_path:
            continue
        try:
            snapshot[rel_path] = (root / rel_path).read_bytes()
        except OSError:
            continue
    return snapshot


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests tests/test_gates.py::TestFixEngineTierA.test_doc007_dotted_form_rewrite_applies_and_reverifies_clean kind="unit"  # noqa: E501
def apply_tier_a_fixes(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    exclude: tuple[str, ...] = (),
    ticket_id: str | None = None,
    merge_target_ids: MergeTargetKnownIds | None = None,
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
    its rewrites are now ordinary uncommitted changes like any other.

    T-1548: `ticket_id` (the landing ticket's id, `None` outside a land
    context) is threaded to every handler -- every handler except
    `fix_cov002_ticket_directive_insertion` ignores it, matching this
    module's existing precedent of a uniform handler call shape even when
    most handlers do not need every argument (`queue` itself is ignored
    by most pure-`.strata`/doc rewrites already).

    T-2284: every handler's own return value is filtered through
    `filter_fixes_by_scope_and_lease` (`frob.gates._fix_engine_scope`)
    BEFORE it is added to `applied`/the manifest -- a fix outside the
    landing ticket's declared scope, or on a file another ticket holds a
    live lease on, is reverted on disk right here and never counted as
    applied. Reported at WARNING (visible in `frob ticket land`'s own
    output, not only a debug log) so a skip is disclosed exactly as
    loudly as an applied fix. A no-op, byte-identical to pre-T-2284
    behavior, whenever `ticket_id` is `None` (bare `frob check --fix`,
    no landing ticket to scope against) or nothing a handler touched
    happens to be out of bounds.

    T-2351: `pre_fix_snapshot` is captured ONCE, here, before any
    handler in the loop below runs -- every handler's own writes happen
    against the SAME worktree state this snapshot was taken from, so one
    capture up front covers the whole batch. Threaded to
    `filter_fixes_by_scope_and_lease` so a disqualified fix is reverted
    back to the ticket's own pre-handler state, not to `HEAD` -- see
    `_fix_engine_scope._revert_fix_file`'s own docstring for why `HEAD`
    silently discarded real, uncommitted, in-scope work when this
    function runs (as it always does, T-1175) BEFORE `frob ticket
    land`'s own pre-land wip-commit step.

    T-2400: `merge_target_ids`, when given (only by `frob ticket land`'s
    pre-land call site), is threaded to every handler alongside
    `ticket_id` -- only `fix_tick006_phantom_refile` reads it, to
    resolve a Done report's citation against the land's actual merge
    target instead of just this (possibly stale) worktree ledger. `None`
    for a bare `frob check --fix`, byte-identical to pre-T-2400
    behavior."""
    applied: list[FixApplied] = []
    pre_fix_snapshot = _snapshot_dirty_files(root)
    for rule_id, handler in TIER_A_HANDLERS.items():
        if rule_id in exclude:
            _log.info("tier-a fixes: %s excluded by caller", rule_id)
            continue
        fixes = handler(root, snapshot, queue, ticket_id, merge_target_ids)
        kept, skipped = filter_fixes_by_scope_and_lease(
            root, queue, ticket_id, fixes, pre_fix_snapshot
        )
        for skip in skipped:
            _log.warning(
                "tier-a fixes: SKIPPED %s %s:%d -- %s",
                skip.rule,
                skip.file,
                skip.line,
                skip.reason,
            )
        applied.extend(kept)
        write_autofix_manifest(root, applied)
    clear_autofix_manifest(root)
    return applied
