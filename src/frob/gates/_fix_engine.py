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

from frob.gates._fix_engine_shared import (
    FixApplied,
    _write_text,
    clear_autofix_manifest,
    write_autofix_manifest,
)
from frob.gates._fix_engine_sync import (
    fix_cov002_ticket_directive_insertion,
    fix_reg010_registry_sync,
    fix_rel002_release_sync,
    fix_sys100_extended_whole_node_grant,
    fix_sys100_may_via_union,
    fix_waive004_stale_waiver,
)
from frob.gates._fix_engine_text import (
    fix_e501_merge_introduced,
    fix_fmt001_directive_wrap,
    fix_suppress001_paired_suppression,
)
from frob.graph import EdgeKind, GraphSnapshot
from frob.tickets import Ticket, TicketQueue
from frob.tickets._provisional import is_draft_id

_log = logging.getLogger(__name__)


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
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_refiles_and_rewrites_citation \
# kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineTierA.test_tick006_known_id_is_never_touched \
# kind="unit"
def fix_tick006_phantom_refile(root: Path, queue: TicketQueue) -> list[FixApplied]:
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
    SECOND phantom."""
    from frob.tickets._store import load_archive

    archived = load_archive(root)
    known_ids = set(queue.tickets) | (
        set(archived.danger_ok) if archived.is_ok else set()
    )
    applied: list[FixApplied] = []
    for ticket in sorted(queue.tickets.values(), key=lambda t: t.id):
        applied.extend(_tick006_refile_for_ticket(root, ticket, known_ids))
    return applied


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


def _tick006_refile_for_ticket(
    root: Path, ticket: Ticket, known_ids: set[str]
) -> list[FixApplied]:
    """One ticket's own share of `fix_tick006_phantom_refile`'s work:
    scan its Done report for phantom citations, refile a real ticket for
    each, and rewrite them in place -- split out of the parent purely to
    keep it under ARCH001's line threshold. Mutates `known_ids` in place
    (adds each newly refiled id) so a LATER ticket in the same pass never
    double-files against an id THIS pass already claimed."""
    from frob.gates._tickets_gate import _tick006_done_report_text, _tick006_phantom_ids
    from frob.tickets import new_ticket
    from frob.tickets._new_renumber import _rewrite_body_prose_references
    from frob.tickets._store import write_ticket

    done_report_text = _tick006_done_report_text(ticket.body)
    if not done_report_text:
        return []
    applied: list[FixApplied] = []
    current_body = ticket.body
    for tid in _tick006_phantom_ids(done_report_text):
        if tid in known_ids:
            continue
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
            continue
        new_id = created.danger_ok.id
        known_ids.add(new_id)
        current_body, hits = _rewrite_body_prose_references(current_body, {tid: new_id})
        if hits:
            applied.append(
                FixApplied(
                    rule="TICK006",
                    file="tickets.md",
                    line=0,
                    detail=f"{tid} -> {new_id} (refiled, cited by {ticket.id})",
                )
            )
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
TIER_A_HANDLERS: dict[
    str, Callable[[Path, GraphSnapshot, TicketQueue, "str | None"], list[FixApplied]]
] = {
    "DOC007": lambda root, snapshot, queue, ticket_id: fix_doc007_dotted_form(
        root, snapshot
    ),
    "DOC002": lambda root, snapshot, queue, ticket_id: fix_doc002_unique_slug(
        root, snapshot
    ),
    "FMT001": lambda root, snapshot, queue, ticket_id: fix_fmt001_directive_wrap(
        root
    ),
    "SUPPRESS001": (
        lambda root, snapshot, queue, ticket_id: fix_suppress001_paired_suppression(
            root, snapshot
        )
    ),
    "REG010": lambda root, snapshot, queue, ticket_id: fix_reg010_registry_sync(root),
    "REL002": lambda root, snapshot, queue, ticket_id: fix_rel002_release_sync(root),
    "SYS100": lambda root, snapshot, queue, ticket_id: _fix_sys100_both_cases(root),
    "E501": lambda root, snapshot, queue, ticket_id: fix_e501_merge_introduced(root),
    "COV002": (
        lambda root, snapshot, queue, ticket_id: fix_cov002_ticket_directive_insertion(
            root, snapshot, queue, ticket_id
        )
    ),
    "TICK002": lambda root, snapshot, queue, ticket_id: fix_tick002_renumber(
        root, queue
    ),
    "TICK006": lambda root, snapshot, queue, ticket_id: fix_tick006_phantom_refile(
        root, queue
    ),
    "WAIVE004": lambda root, snapshot, queue, ticket_id: fix_waive004_stale_waiver(
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
    ticket_id: str | None = None,
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
    by most pure-`.strata`/doc rewrites already)."""
    applied: list[FixApplied] = []
    for rule_id, handler in TIER_A_HANDLERS.items():
        if rule_id in exclude:
            _log.info("tier-a fixes: %s excluded by caller", rule_id)
            continue
        applied.extend(handler(root, snapshot, queue, ticket_id))
        write_autofix_manifest(root, applied)
    clear_autofix_manifest(root)
    return applied
