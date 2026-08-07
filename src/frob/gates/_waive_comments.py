"""frob.gates._waive_comments -- WAIVE006/007 (stale/dangling waiver ticket
refs, both the `frob:waive` comment channel and the `.strata` `waive`
clause channel) and PLACE001 (misplaced `frob:` directive) gate families,
split out of `frob.gates._waive` (T-1081, clearing that module's ARCH102
finding -- these three rules share one cohesive concern: is a directive
COMMENT sitting somewhere sound, as opposed to `_waive.py`'s own
directive-VALIDATION and match/apply-spine clusters).
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.gates._waive import _waive_edges
from frob.graph import GraphSnapshot
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile, RawComment, RawSymbol
from frob.logging import get_logger
from frob.tickets import TicketQueue, TicketState

_log = get_logger(__name__)


# T-0779 (audit H2): a waiver justified by "this is pending ticket T-XXXX"
# must not outlive T-XXXX -- the five LINT004 kill-switch waivers cited
# T-0200 as the follow-on ticket to build for months after T-0200 closed,
# and nothing re-litigated them. WAIVE006 resolves every ticket id a
# waiver BINDS ITSELF to (never a bare historical mention) against the
# ledger+archive; DONE or DROPPED there means the waiver has outlived its
# own justification and must be re-justified or removed.
#
# Calibration (the hard part): a waiver's reason prose routinely narrates
# history ("kill-switch mechanism exists (T-0200/T-0778) but ... -- tracked
# in T-draft-8cd37914") without the mention being a live claim that T-0200
# is still open or still the reason the gap is excused -- T-0778 rewrote
# exactly this class of waiver to cite an open follow-on while HISTORICALLY
# mentioning the now-closed T-0200 that built the underlying mechanism.
# WAIVE006 must not fire on that. Two things count as binding:
#   1. An explicit ticket attribute (`frob:waive RULE reason="..."
#      ticket="T-####"`, or a strata `waive "RULE" reason "..." ticket
#      "T-####";` clause) -- the author wrote down, structurally, "this is
#      what tracks the gap".
#   2. Specific "still pending on this ticket" phrasing INSIDE the reason
#      text itself (`_WAIVE006_BINDING_PHRASE_RES`) -- "pending T-####" and
#      "T-#### is the follow-on ticket" are the two shapes this repo's own
#      history (T-0412/T-0753 debt-style waivers, the pre-T-0778 LINT004
#      waivers) has actually produced. A bare `(T-0200/T-0778)` aside or a
#      `T-0200 built a real kill switch` narration is neither shape, so it
#      is never extracted -- only a ticket reference the reason text itself
#      claims is the live justification counts.
_WAIVE006_TICKET_ID_RE = r"T-\d+"
_WAIVE006_BINDING_PHRASE_RES = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        rf"\bpending\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bpending[\s-]+on\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\b({_WAIVE006_TICKET_ID_RE})\s+is\s+the\s+follow-on\s+ticket\b",
        rf"\bfollow-on\s+ticket\s*(?:is|:)?\s*({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bblocked\s+on\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bwaiting\s+on\s+({_WAIVE006_TICKET_ID_RE})\b",
    )
)


def _waive006_binding_ticket_refs(reason: str) -> set[str]:
    """Ticket ids `reason` BINDS ITSELF to via one of
    `_WAIVE006_BINDING_PHRASE_RES`'s explicit "still pending on this
    ticket" phrasings -- never a bare id mention in narration prose (the
    T-0778 calibration case this module docstring section explains)."""
    refs: set[str] = set()
    for pattern in _WAIVE006_BINDING_PHRASE_RES:
        refs.update(match.group(1) for match in pattern.finditer(reason))
    return refs


def _waive006_stale_ticket(ticket_ids: set[str], queue: TicketQueue) -> str | None:
    """The first `ticket_ids` entry that resolves in `queue` (active+archive)
    to a DONE/DROPPED ticket, or `None` if every reference is either open or
    unresolvable. Unresolvable ids (typos, draft ids not yet finalized) are
    deliberately NOT flagged here -- that is a different, separate honesty
    gap from "this ticket closed and nobody re-reviewed the waiver"."""
    for ticket_id in sorted(ticket_ids):
        target = queue.tickets.get(ticket_id)
        if target is not None and target.state in (
            TicketState.DONE,
            TicketState.DROPPED,
        ):
            return ticket_id
    return None


def _waive006_violation(
    *, file: str, line: int, site: str, rule_and_target: str, stale: str
) -> Violation:
    """The single WAIVE006 `Violation` for one stale-waiver site (shared by
    both the `frob:waive` comment channel and the `.strata` `waive` clause
    channel, so the message shape is identical regardless of directive
    flavor)."""
    _log.error(
        "WAIVE006: %s (%s) binds to closed ticket %s", site, rule_and_target, stale
    )
    return Violation(
        rule="WAIVE006",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"WAIVE006: {site} waives {rule_and_target}, bound to ticket "
            f"{stale}, which is DONE/DROPPED; a waiver justified by a "
            f"pending ticket must not outlive it -- re-justify with a "
            f"current reason (and, if still needed, an open follow-on "
            f"ticket) or remove the waiver now that the gap it excused "
            f"has presumably been addressed"
        ),
    )


# frob:enforces CHK-GATE-WAIVE006
def _waive006_comment_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006 (`frob:waive` comment channel): a waiver whose `ticket=`
    attribute, or whose `reason=` text binds itself via
    `_waive006_binding_ticket_refs`, names a ticket that is DONE or DROPPED
    in the ledger+archive."""
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        reason = edge.attrs.get("reason", "")
        refs = _waive006_binding_ticket_refs(reason)
        attr_ticket = edge.attrs.get("ticket", "")
        if attr_ticket:
            refs.add(attr_ticket)
        if not refs:
            continue
        stale = _waive006_stale_ticket(refs, queue)
        if stale is None:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        violations.append(
            _waive006_violation(
                file=file,
                line=line,
                site=edge.src,
                rule_and_target=f"frob:waive {edge.target}",
                stale=stale,
            )
        )
    return tuple(violations)


# `waive "RULE[:SUBTARGET]" reason "..." [ticket "T-####"]` -- strata-core's
# `.strata` grammar (docs/strata/waive.md, `frob.strata._waive`'s module
# docstring). Deliberately a plain single-line regex scan here rather than
# a `strata_core` parse+elaborate: this rule only needs the literal
# `reason`/`ticket` string attrs off each clause (no capability/threat
# model reasoning), and scanning avoids paying the native-extension import
# cost (T-0135's standalone-install posture) just to read two string
# fields. Every live `waive` clause in this repo today is single-line
# (T-0778's own rewrite); a clause split across lines is not matched --
# documented limitation, not silently wrong (it simply finds nothing to
# flag there, same fail-open posture `_debt_is_expired` takes on an
# unparseable `until`).
_STRATA_WAIVE_RE = re.compile(
    r'waive\s+"(?P<rule>[^"]+)"\s+reason\s+"(?P<reason>(?:[^"\\]|\\.)*)"'
    r'(?:\s+ticket\s+"(?P<ticket>[^"]*)")?\s*;'
)


def _strata_waive_sites(root: Path) -> list[tuple[str, int, str, str, str]]:
    """Every `(file, line, rule, reason, ticket)` `waive` clause found by a
    line scan of every `.strata` file under this repo's design dir (opt-in:
    empty when no design dir exists), minus `[graph].exclude` matches --
    same exclusion posture every other file-walking gate in this module
    already applies (`is_excluded`/`load_exclude_globs`)."""
    root = Path(root)
    from frob.gates import _design_dir  # local: avoid init-time circularity

    design_dir = root / _design_dir(root)
    if not design_dir.is_dir():
        return []
    exclude_globs = load_exclude_globs(root)
    sites: list[tuple[str, int, str, str, str]] = []
    for path in sorted(iter_files(design_dir, suffix=".strata")):
        rel = path.relative_to(root).as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("_strata_waive_sites: could not read %s: %s", rel, exc)
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _STRATA_WAIVE_RE.search(line)
            if match is None:
                continue
            sites.append(
                (
                    rel,
                    lineno,
                    match.group("rule"),
                    match.group("reason"),
                    match.group("ticket") or "",
                )
            )
    return sites


# frob:enforces CHK-GATE-WAIVE006
def _waive006_strata_violations(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006 (`.strata` `waive` clause channel): the same stale-waiver
    check `_waive006_comment_violations` runs for `frob:waive` comments,
    applied to every `waive "RULE" reason "..." [ticket "..."]` clause
    `_strata_waive_sites` finds."""
    violations: list[Violation] = []
    for rel, line, rule, reason, ticket in _strata_waive_sites(root):
        refs = _waive006_binding_ticket_refs(reason)
        if ticket:
            refs.add(ticket)
        if not refs:
            continue
        stale = _waive006_stale_ticket(refs, queue)
        if stale is None:
            continue
        violations.append(
            _waive006_violation(
                file=rel,
                line=line,
                site=f"{rel}:{line}",
                rule_and_target=f'waive "{rule}"',
                stale=stale,
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
def waive006_gate(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006: every stale-waiver finding across both waiver channels
    (`frob:waive` comments and `.strata` `waive` clauses) -- see the module
    comment above `_waive006_binding_ticket_refs` for the full rule design
    and the binding-vs-historical-mention calibration."""
    return (
        *_waive006_comment_violations(snapshot, queue),
        *_waive006_strata_violations(root, queue),
    )


# T-0808 (T-0779 reviewer finding): WAIVE006 deliberately skips a binding
# ticket ref that does not resolve to any ticket at all (active or
# archive) -- that is a different honesty gap, not WAIVE006's "closed
# ticket" case, and was silently unflagged. The real incident this closes:
# four `design/frob.strata` waivers bound to `T-draft-8cd37914`, which was
# renumbered to `T-0803` at land -- the waivers kept citing a ticket id
# that no longer (and now never again) resolves, a permanent silent
# waiver with nothing left to re-litigate it.
#
# Exemption: EVERY `T-draft-*` id is exempt from WAIVE007, unconditionally
# -- not just ones referenced by a still-live worktree lease. A narrower
# "exempt only if a live lease still claims this draft id" rule was
# considered and rejected: it would require this gate to cross-reference
# `frob.tickets._leases` state that is worktree-local and routinely absent
# in the very run (a landed/merged checkout, CI, another agent's worktree)
# where the gate needs to be trustworthy, making the exemption itself flaky
# across environments -- exactly the kind of environment-dependent gate
# result this repo's gates avoid elsewhere. Drafts are worktree-local
# transients by construction (`frob.tickets._models` mints `T-draft-<hex>`
# only inside an active worktree, and `frob ticket land` always renumbers
# them to a real `T-####` id before the ledger is shared) -- so ANY
# `T-draft-*` id a gate run observes is either still in-progress (not yet
# landed, not a dangling reference at all -- the id simply has not been
# minted into the real ledger this checkout sees) or was already
# renumbered away and is now permanently unresolvable by design, a state
# WAIVE006 already treats as out of scope for the identical reason (see
# `_waive006_stale_ticket`'s docstring). Flagging a renumbered draft as
# "dangling" would fire on every merged waiver written before its own
# ticket landed, forever, which is noise WAIVE007 exists to avoid
# creating, not add.
def _waive007_is_exempt_dangling_ref(ticket_id: str) -> bool:
    """`True` for any `T-draft-*` id: worktree-local transient by
    construction (see the module comment above), never a WAIVE007
    finding regardless of whether it currently resolves."""
    return ticket_id.startswith("T-draft-")


def _waive007_violation(
    *, file: str, line: int, site: str, rule_and_target: str, dangling: str
) -> Violation:
    """The single WAIVE007 `Violation` for one waiver site whose binding
    ticket ref does not resolve to any ticket (shared by both waiver
    channels, mirroring `_waive006_violation`'s shape)."""
    _log.warning(
        "WAIVE007: %s (%s) binds to unresolvable ticket %s",
        site,
        rule_and_target,
        dangling,
    )
    return Violation(
        rule="WAIVE007",
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(
            f"WAIVE007: {site} waives {rule_and_target}, bound to ticket "
            f"{dangling}, which does not resolve to any ticket (active or "
            f"archive) -- a typo, or a draft id renumbered at land; "
            f"re-point the waiver at the real ticket id or remove the "
            f"stale binding"
        ),
    )


# frob:enforces CHK-GATE-WAIVE007
def _waive007_comment_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007 (`frob:waive` comment channel): a waiver whose `ticket=`
    attribute, or whose `reason=` text binds itself via
    `_waive006_binding_ticket_refs` (the same binding-vs-mention
    extraction WAIVE006 uses), names a ticket id that resolves to nothing
    in the ledger+archive and is not `_waive007_is_exempt_dangling_ref`."""
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        reason = edge.attrs.get("reason", "")
        refs = _waive006_binding_ticket_refs(reason)
        attr_ticket = edge.attrs.get("ticket", "")
        if attr_ticket:
            refs.add(attr_ticket)
        if not refs:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        # frob:waive PERF004 reason="own distinct refs set per waive edge, not a shared re-sort"  # noqa: E501
        for ticket_id in sorted(refs):
            if ticket_id in queue.tickets:
                continue
            if _waive007_is_exempt_dangling_ref(ticket_id):
                continue
            violations.append(
                _waive007_violation(
                    file=file,
                    line=line,
                    site=edge.src,
                    rule_and_target=f"frob:waive {edge.target}",
                    dangling=ticket_id,
                )
            )
    return tuple(violations)


# frob:enforces CHK-GATE-WAIVE007
def _waive007_strata_violations(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007 (`.strata` `waive` clause channel): the same dangling-
    binding-ref check `_waive007_comment_violations` runs for `frob:waive`
    comments, applied to every `waive "RULE" reason "..." [ticket "..."]`
    clause `_strata_waive_sites` finds."""
    violations: list[Violation] = []
    for rel, line, rule, reason, ticket in _strata_waive_sites(root):
        refs = _waive006_binding_ticket_refs(reason)
        if ticket:
            refs.add(ticket)
        if not refs:
            continue
        # frob:waive PERF004 reason="own distinct refs set per waive clause site, not a shared re-sort"  # noqa: E501
        for ticket_id in sorted(refs):
            if ticket_id in queue.tickets:
                continue
            if _waive007_is_exempt_dangling_ref(ticket_id):
                continue
            violations.append(
                _waive007_violation(
                    file=rel,
                    line=line,
                    site=f"{rel}:{line}",
                    rule_and_target=f'waive "{rule}"',
                    dangling=ticket_id,
                )
            )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
def waive007_gate(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007: every dangling-binding-ref finding across both waiver
    channels (`frob:waive` comments and `.strata` `waive` clauses) -- see
    the module comment above `_waive007_is_exempt_dangling_ref` for the
    full rule design and the `T-draft-*` exemption rationale."""
    return (
        *_waive007_comment_violations(snapshot, queue),
        *_waive007_strata_violations(root, queue),
    )


# frob:ticket T-0504
# PLACE001 was first prototyped as "distance from the class's own span
# start" and DELIBERATELY DROPPED (T-0470) before landing: that heuristic
# fired on this repo's own widespread, legitimate idiom of per-field
# `frob:waive`/`frob:ticket` comments documenting one field deep inside a
# large pydantic config class (e.g. `src/frob/app/config.py`'s
# `AppConfig`, `frob:waive SCOPE001` at line 212, 150+ lines past the
# class's `class AppConfig:` line) -- fields are not `RawSymbol`s (only
# FUNCTION/METHOD/CLASS/CONST/TYPE are), so a directive above one always
# falls back to the enclosing class by construction, and doing so far
# from the class top is completely intentional there, not mis-scoped.
#
# T-0504 replaces that raw-distance signal with the materially different
# one this comment's own predecessor named as the real fix: does a
# nearby REAL symbol exist that the directive plausibly SHOULD have
# bound to via `following` but didn't reach, with nothing but blank
# lines/comments/decorators between the directive and that symbol? The
# per-field idiom always has genuine field-assignment CODE in that gap
# (the very thing that makes it a field and not a stray comment), so it
# is excluded by construction rather than by distance -- see
# `_place001_missed_symbol`'s docstring for the full argument and
# `TestPlace001Gate` for both the non-vacuous positive (a directive
# separated from its intended `def` by one blank line too many) and the
# AppConfig-shaped negative (a directive above a field, real code before
# the next real method).
_PLACE001_LOOKAHEAD = 10


# frob:ticket T-0504
def _place001_missed_symbol(
    comment: RawComment,
    symbols: tuple[RawSymbol, ...],
    lines: list[str],
) -> RawSymbol | None:
    """The nearby REAL symbol (within `_PLACE001_LOOKAHEAD` lines) that a
    class-fallback-bound `frob:` directive plausibly intended but missed
    via `_find_following_symbol`'s narrower window -- `None` if no such
    symbol exists, or if genuine code (anything other than a blank line,
    a `#`/`//` comment, or a decorator line) sits between the directive
    and the candidate.

    That "genuine code in between" check is the whole soundness argument
    (T-0504): the only way `following` can miss a REAL symbol that is
    still close by is a run of blank lines, stacked comments, or
    decorators wider than `_FOLLOWING_SYMBOL_WINDOW` -- none of which is
    itself an intervening obligation the directive could instead belong
    to. The per-field pydantic idiom this ticket must NOT fire on always
    has actual field-assignment code in that gap (that is what makes it
    a field), so it can never produce a candidate here regardless of how
    close or far the class's next real method sits.
    """
    end = comment.span[1]
    candidates = [
        sym for sym in symbols if end < sym.span[0] <= end + _PLACE001_LOOKAHEAD
    ]
    if not candidates:
        return None
    candidate = min(candidates, key=lambda sym: sym.span[0])
    for lineno in range(end + 1, candidate.span[0]):
        if lineno - 1 >= len(lines):
            break
        stripped = lines[lineno - 1].strip()
        if stripped == "" or stripped.startswith(("#", "//", "@")):
            continue
        return None
    return candidate


# frob:ticket T-0504
def _place001_bindings(
    comments: tuple[RawComment, ...], path: str
) -> dict[int, tuple[str, bool]]:
    """`comment_id -> (resolved_src, via_following)` for every comment in
    `comments`, mirroring `frob.graph.dsl._resolve_block_srcs`'s exact
    stacked-comment-propagation algorithm (order, carry state) but ALSO
    tagging whether the binding was reached via a `following` match
    (direct, or propagated backward from a later comment's own resolved
    `following` in the same contiguous block, T-0313) versus a genuine
    `enclosing`/bare-path fallback.

    This distinction is the entire soundness argument for PLACE001: a
    `frob:doc`/`frob:ticket` comment placed directly above `class Foo:`
    resolves via `following` straight to `Foo` (correct and intentional,
    `via_following=True`) even though `Foo` is a CLASS -- checking only
    "did this resolve to a class" (as `_resolve_block_srcs`'s plain
    output would tempt) cannot tell that apart from a directive genuinely
    stuck at the class-fallback because it sits somewhere INSIDE the
    class body with no reachable `following` target at all
    (`via_following=False`). Only the latter is what T-0504's placement
    check should ever consider.
    """
    from frob.graph.dsl import _enclosing_src

    order = sorted(range(len(comments)), key=lambda i: comments[i].span[0])
    resolved: dict[int, tuple[str, bool]] = {}
    carry_start: int | None = None
    carry_src: str | None = None
    for idx in reversed(order):
        comment = comments[idx]
        if comment.following is not None:
            src = f"{path}::{comment.following}"
        elif carry_src is not None and comment.span[1] + 1 == carry_start:
            src = carry_src
        else:
            resolved[idx] = (_enclosing_src(comment, path), False)
            carry_start = None
            carry_src = None
            continue
        resolved[idx] = (src, True)
        carry_start = comment.span[0]
        carry_src = src
    return resolved


# frob:ticket T-0504
# frob:enforces CHK-GATE-PLACE001
def _place001_file(root: Path, file: str) -> tuple[Violation, ...]:
    """PLACE001 findings for one file: a `frob:` directive whose fully
    resolved binding (`_place001_bindings`, the same stacked-comment-aware
    resolution `parse_directives` itself uses) is a genuine class
    FALLBACK (`via_following=False`, not a directive that correctly
    resolved via `following` straight to a class it precedes), where
    `_place001_missed_symbol` finds a real symbol the directive plausibly
    should have reached instead.

    Re-parses `file` directly (root-relative, like `_cov006`/`_cov005`)
    rather than reusing `GraphSnapshot` -- the snapshot only carries
    already-resolved `Edge`s, not the per-comment `following`/`enclosing`
    detail this check needs.
    """
    from frob.lang import parse_file

    result = parse_file(root / file)
    if result.is_err:
        return ()
    parsed = result.danger_ok
    try:
        lines = (root / file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.warning("PLACE001: could not read %s: %s", file, exc)
        return ()
    symbol_by_qualname = {sym.qualname: sym for sym in parsed.symbols}
    resolved = _place001_bindings(parsed.comments, file)
    violations: list[Violation] = []
    for comment_id, comment in enumerate(parsed.comments):
        violation = _place001_comment_violation(
            file, comment_id, comment, resolved, symbol_by_qualname, parsed, lines
        )
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:ticket T-0598
def _place001_comment_violation(
    file: str,
    comment_id: int,
    comment: RawComment,
    resolved: dict[int, tuple[str, bool]],
    symbol_by_qualname: dict[str, RawSymbol],
    parsed: ParsedFile,
    lines: list[str],
) -> Violation | None:
    """One `frob:` directive's PLACE001 finding, or `None` if it does not
    class-fall-back to a real missed symbol (`_place001_file`'s per-comment
    body, split out for ARCH001 -- T-0598)."""
    if not comment.text.startswith("frob:"):
        return None
    src, via_following = resolved[comment_id]
    if via_following:
        return None
    _prefix, sep, qualname = src.partition("::")
    if not sep:
        return None
    enclosing_sym = symbol_by_qualname.get(qualname)
    if enclosing_sym is None or enclosing_sym.kind != SymbolKind.CLASS:
        return None
    missed = _place001_missed_symbol(comment, parsed.symbols, lines)
    if missed is None:
        return None
    _log.debug(
        "PLACE001: %s:%s directive class-falls-back to %s, missed %s",
        file,
        comment.span[0],
        qualname,
        missed.qualname,
    )
    return Violation(
        rule="PLACE001",
        severity=Severity.WARN,
        file=file,
        line=comment.span[0],
        message=(
            f"PLACE001: {file}:{comment.span[0]} frob: directive "
            f"falls back to enclosing class {qualname!r}, but "
            f"{missed.qualname!r} starts at line {missed.span[0]} "
            f"with nothing but blank lines/comments/decorators in "
            f"between -- likely intended for that symbol; move "
            f"the directive within the following-window, or "
            f"confirm the class binding is intentional"
        ),
    )


# frob:ticket T-0504
def _place001(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PLACE001 (advisory): a `frob:` directive that class-falls-back
    (`_place001_file`) instead of reaching a real, nearby symbol via
    `following` -- a likely mis-scoped directive, not raw distance from
    the class's own span start (T-0470's dropped prototype; see the
    comment above `_PLACE001_LOOKAHEAD` for the full history).

    WARN severity: best-effort, name/position-based (same tier as
    COV006) -- a finding is a prompt to double check, not proof the
    directive is wrong.
    """
    files = sorted({symref.split("::", 1)[0] for symref in snapshot.symbols})
    violations: list[Violation] = []
    for file in files:
        violations.extend(_place001_file(root, file))
    return tuple(violations)
