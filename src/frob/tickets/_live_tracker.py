"""T-0854: the T-0605-orphaned-41-rows incident class, closed mechanically.

Landing/closing T-0605 instantly turned 41 `docs/design/registry/
patterns.yaml` rows with `disposition: "deferred:T-0605"` into main-wide
REG003 errors -- discovered only on the NEXT `frob check`, after the close
was already final and irreversible. `frob.gates`'s WAIVE006 already models
the identical hazard for `frob:waive ... ticket=<id>` bindings (T-1559
extends the same scan to WIRE001/WIRE002's `follow_up=<id>` binding, the
same hazard for a different waiver family -- see `_WAIVER_TICKET_PATTERN`),
but neither
check ran AT CLOSE TIME for the ticket about to disappear -- both only ever
caught it retroactively, one `frob check` too late.

This module is the close/land-time preflight: a plain, self-contained
grep-shaped scan (`live_tracker_citations`) for every site that still cites
`ticket_id` as its live tracker -- a registry `disposition: "deferred:
<id>"`/`"tracked_by:<id>"` value, or a `ticket=`/`ticket "..."` waiver
attribute (both the `frob:waive` comment-directive grammar and the
`.strata` `waive` clause grammar) -- so `frob ticket close`/`frob ticket
land` can refuse BEFORE the ticket disappears, not after.

Deliberately NOT the `frob.gates` `_waive006_comment_violations`/registry-
model machinery: those build a full `GraphSnapshot`/parsed-registry-entry
index, expensive to build from scratch on every close and already cached
only for a full `frob check` run, not a single `frob ticket close`. `git
grep` over the repo's own index (`frob.gitio.run_argv`, same guarded-
subprocess seam every other git spawn in this package uses) is the
"targeted grep-shaped scan, not a full registry parse per close" the
ticket's own plan calls for -- a literal, bounded text search, no YAML
parse and no graph build. A `git grep`/`ls-files` failure (not a git work
tree, `FROB_DISABLE_EXEC=1`, ...) degrades to "no citations found" rather
than refusing every close forever on an unrelated infra failure -- this
check is additive to the pre-existing evidence gates, mirroring T-0755's
own posture for `_check_mutation_evidence`.

T-0854 rework (reviewer MAJOR finding): an earlier revision exempted a
citation purely because its FILE matched the closing ticket's declared
`scope` glob, with no check that the citing LINE itself had actually been
touched. That is gameable -- any ticket could `frob ticket scope --add`
the registry yaml (or a source file carrying the waiver) and close with
the row/attribute still citing it unchanged, defeating the T-0605
protection entirely. The exemption is now diff-aware instead: a citation
found in the CURRENT tree is only exempt when that exact citation (same
file, same text) did NOT already exist, unchanged, at `base_ref` -- i.e.
it is either brand new (a fresh file/row this very diff introduces,
self-consistent by construction) or was re-pointed to name something else
(so it no longer matches `ticket_id` in the current tree at all, and
never even reaches this comparison). A citation that is byte-identical at
both `base_ref` and the current tree is untouched by this diff and is
never exempt, regardless of which files the ticket's `scope` declares."""

from __future__ import annotations

import re
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

# `disposition: "deferred:T-0605"` / `disposition: 'tracked_by:T-0605'` --
# the registry grammar's two "still open, tracked elsewhere" dispositions
# (`frob.registry._models.parse_disposition`); `duplicate_of:` is excluded
# on purpose -- a duplicate_of citation survives its target's close fine
# (it never claimed the target itself still had open work).
_REGISTRY_LIVE_KINDS = ("deferred", "tracked_by")

# `frob:waive RULE reason="..." ticket=T-0605` (comment channel, `=`,
# quotes optional) and the `.strata` twin `waive "RULE" reason "..."
# ticket "T-0605"` (bare space, but the value itself is ALWAYS quoted in
# that grammar) -- deliberately NOT `ticket\s+T-0605` unquoted-and-
# unattributed: that also matches an ordinary CLI invocation/log line like
# `--ticket T-0605` (a real false-positive class hit in `.frob/
# telemetry.jsonl` during T-0854's own testing), which cites nothing as a
# live tracker at all.
# T-1559: the WIRE001/WIRE002 `follow_up=` binding (`frob.gates._wire.
# _wire002_violations`'s own attribute) is the SAME "this ticket is still
# cited as live tracker" hazard `ticket=` already covers, for a different
# waiver family (WIRE001's deferred-wiring waivers, not WAIVE006's own).
# The 2026-08-05 incident this ticket fixes: T-1490/T-1488 landed and
# closed while 16 `frob:waive WIRE001 ... follow_up="T-1490"`-shaped
# directives still bound them -- WIRE002 caught it only on the NEXT `frob
# check`, one check too late, exactly the T-0605 shape this module
# already exists to close for `ticket=`. Folded into the SAME pattern
# (one `git grep -E` alternation) rather than a parallel scan, since both
# are "a comment attribute equals this ticket id" citations differing
# only in attribute name.
# frob:ticket T-1633
# Each attribute alternative is LEFT-ANCHORED by an explicit leading-character
# alternation rather than a lookbehind: this pattern is handed to `git grep -E`
# (POSIX ERE), which has no lookbehind at all. Without the anchor, `ticket=`
# matched inside any longer identifier ending in it -- `active_ticket=T-1582`
# in ordinary Done-report prose read as a live-tracker citation and refused a
# land.
_LEFT = r"(^|[^A-Za-z0-9_.-])"
_WAIVER_TICKET_PATTERN = (
    _LEFT + r'ticket="?{id}"?\b'
    r"|" + _LEFT + r'ticket\s+"{id}"'
    r"|" + _LEFT + r'follow_up="?{id}"?\b'
)

# frob:ticket T-1633
# The waiver grep EXCLUDES the ledger. A `frob:waive ... ticket=<id>` /
# `follow_up=<id>` directive is a source-code comment; it never legitimately
# appears in tickets.md/tickets-archive.md/tickets/**, where every occurrence
# is narrative -- a Done report quoting a command, an incident write-up
# quoting the very pattern that misfired. Scanning prose for declarations
# refused two real lands (T-1582, twice) and would keep doing so however
# precise the regex became.
_WAIVER_PATHSPEC = (
    ":(exclude)tickets.md",
    ":(exclude)tickets-archive.md",
    ":(exclude)tickets/**",
)


# `docs/design/registry/*.yaml` -- the one pathspec the registry-
# disposition grep is scoped to (the waiver grep runs repo-wide, no
# pathspec, since a `frob:waive`/`.strata waive` citation can live
# anywhere).
_REGISTRY_PATHSPEC = "docs/design/registry/*.yaml"


def _registry_pattern(ticket_id: str) -> str:
    """The `git grep -E` pattern for a registry `disposition:` value
    naming `ticket_id` under any of `_REGISTRY_LIVE_KINDS`."""
    kinds = "|".join(_REGISTRY_LIVE_KINDS)
    return rf'disposition:\s*["\']?({kinds}):{re.escape(ticket_id)}\b'


# frob:ticket T-1559
def _waiver_pattern(ticket_id: str) -> str:
    """The `git grep -E` pattern for a waiver `ticket=`/`ticket "..."`
    attribute (WAIVE006's own binding) OR a `follow_up=` attribute
    (WIRE001/WIRE002's binding, T-1559) naming `ticket_id`."""
    return _WAIVER_TICKET_PATTERN.format(id=re.escape(ticket_id))


def _git_grep(
    root: Path,
    pattern: str,
    *,
    pathspec: str | tuple[str, ...] | None,
    revision: str | None = None,
) -> tuple[str, ...] | None:
    """`git grep -n -E pattern [<revision>] [-- pathspec]` under `root`,
    returning `file:line:text` lines. `revision=None` (the default) greps
    the current working tree content and NEVER returns `None` for it --
    "cannot scan the current tree at all" (not a git work tree, the exec
    kill switch, ...) degrades to `()`, empty, T-0755's own additive-not-
    fail-closed posture for this class of preflight: nothing to report is
    the honest worst case when the current tree itself is unreadable.

    A real `revision` is different: `None` (as opposed to `()`) means the
    revision itself could not be resolved/read (a typo'd base ref, or a
    default-branch name -- e.g. this function's own `"main"` default --
    that does not actually exist in this repo) as distinct from `()`
    meaning the revision resolved fine but the pattern/pathspec genuinely
    has no match there (the expected, common shape for a brand-new
    file/row). Callers doing a diff-aware base-ref comparison MUST treat
    that distinction as fail-CLOSED (an unresolvable base is "cannot
    prove this citation is new", never "assume it is new") -- collapsing
    both cases to `()` here would make the whole diff-aware exemption
    silently permissive in any repo whose default branch is not literally
    named `"main"` (a real gap caught testing this rework: this sandbox's
    own `git init` default is `master`)."""

    argv = ["git", "-C", str(root), "grep", "-n", "-I", "-E", pattern]
    if revision is not None:
        argv.append(revision)
    if pathspec is not None:
        specs = (pathspec,) if isinstance(pathspec, str) else pathspec
        argv += ["--", *specs]
    lines = _spawn_git_grep(argv, root=root, pattern=pattern, revision=revision)
    if lines is None or revision is None:
        return lines
    return _strip_revision_prefix(lines, revision)


# frob:ticket T-0976
def _spawn_git_grep(
    argv: list[str], *, root: Path, pattern: str, revision: str | None
) -> tuple[str, ...] | None:
    """Spawn one `git grep` `argv` and classify its exit: `None` (see
    `_git_grep`'s own docstring for the `revision`-dependent meaning) on a
    spawn failure or a genuine error exit (>=2); the raw non-empty
    `file:line:text` lines otherwise -- `_git_grep`'s spawn-and-classify
    half, split from its revision-prefix-stripping half."""
    from frob.gitio import run_argv

    spawned = run_argv(argv, timeout_s=15)
    if spawned.is_err:
        _log.warning(
            "tickets: git grep failed under %s (pattern=%r, revision=%r), "
            "skipping live-tracker citation check",
            root,
            pattern,
            revision,
        )
        return None if revision is not None else ()
    result = spawned.danger_ok
    # git grep: 0 = match(es) found, 1 = no match, >=2 = a real error
    # (bad pattern, not a git repo, revision does not resolve, ...) --
    # only >=2 is worth a warning; "no match at this revision" (a brand
    # new file/row) is the expected, common case for a fresh citation.
    if result.returncode not in (0, 1):
        _log.warning(
            "tickets: git grep exited %d under %s (pattern=%r, "
            "revision=%r), skipping live-tracker citation check",
            result.returncode,
            root,
            pattern,
            revision,
        )
        return None if revision is not None else ()
    return tuple(line for line in result.stdout.splitlines() if line)


# frob:ticket T-0976
def _strip_revision_prefix(lines: tuple[str, ...], revision: str) -> tuple[str, ...]:
    """Strip `git grep <revision> -- pathspec`'s `<revision>:` line prefix
    off every line in `lines`, so a base-ref scan's output has the exact
    same `file:line:text` shape a working-tree scan does -- `_git_grep`'s
    revision-prefix-stripping half. See `_git_grep`'s own docstring for
    why leaving the prefix in silently broke `_content_key`'s comparison."""
    prefix = f"{revision}:"
    return tuple(
        line[len(prefix) :] if line.startswith(prefix) else line for line in lines
    )


# frob:ticket T-1970
def _drop_escaped_mentions(lines: tuple[str, ...], pattern: str) -> tuple[str, ...]:
    """T-1970: filter out any `git grep` hit whose match falls entirely
    inside a `frob:quote(...)` escape span -- a MENTION of the citation
    text (the measured incident: a discharge comment quoting
    `follow_up="T-1956"` verbatim while EXPLAINING that the follow-up had
    already been discharged, read as if it were still a live citation),
    never a real one. Re-runs `pattern` (the exact same `git grep -E`
    pattern this module's own patterns are POSIX-ERE-compatible Python
    `re` syntax already) against the TEXT portion of each `file:line:
    text` hit after masking (`frob.graph.dsl.mask_frob_mentions`) --
    a hit that stops matching once masked was a mention wholly inside the
    escape, dropped; a hit that STILL matches (an unescaped citation
    elsewhere on the same line, or the escape did not actually cover the
    match) is kept, unweakened, matching T-1970's own acceptance
    criterion that an unescaped real directive on the same line stays
    honored."""
    from frob.graph.dsl import mask_frob_mentions

    compiled = re.compile(pattern)
    kept: list[str] = []
    for line in lines:
        parts = line.split(":", 2)
        text = parts[2] if len(parts) >= 3 else line
        if compiled.search(mask_frob_mentions(text)):
            kept.append(line)
    return tuple(kept)


def _content_key(line: str) -> str:
    """The `(file, text)` identity of one `git grep -n` result line
    (`file:line:text`), dropping the line NUMBER -- an unrelated edit
    earlier in the same file can shift a citation's line number without
    touching the citation itself, and the diff-aware comparison below
    must not treat that as "re-pointed". Splits on the first TWO colons
    only, since `text` itself routinely contains further colons (YAML
    `key: value`, a `frob:waive` comment)."""
    parts = line.split(":", 2)
    if len(parts) < 3:
        return line
    return f"{parts[0]}:{parts[2]}"


# frob:doc docs/modules/tickets-landing.md#live-tracker-citation-preflight-t-0854
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_registry_deferred_disposition  # noqa: E501
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_comment_waiver_ticket_attribute  # noqa: E501
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_own_scope_citation_excluded  # noqa: E501
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_citation_outside_own_scope_still_flagged  # noqa: E501
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_draft_id_always_clear  # noqa: E501
# frob:tests tests/test_tickets_live_tracker.py::TestLiveTrackerCitations.test_finds_comment_waiver_follow_up_attribute  # noqa: E501
# frob:ticket T-1559
def live_tracker_citations(
    root: Path, ticket_id: str, *, base_ref: str = "main"
) -> tuple[str, ...]:
    """Every `file:line: text` site under `root` that still cites
    `ticket_id` as its live tracker: a registry `deferred:`/`tracked_by:`
    disposition, a waiver `ticket=` attribute (either grammar, WAIVE006's
    own binding), or a waiver `follow_up=` attribute (WIRE001/WIRE002's
    binding, T-1559 -- the 2026-08-05 incident: 16 `frob:waive WIRE001
    ... follow_up="T-1490"`-shaped directives survived T-1490/T-1488's
    close/land and only surfaced as WIRE002 orphans on the NEXT `frob
    check`) -- the exact citation classes the T-0605 incident, WAIVE006,
    and WIRE002 already model, now checked BEFORE the ticket this scan
    names can close/land, not after. Empty means clear to close; a
    non-empty result names every citing row/site so the remedy (file a
    successor ticket and re-point the citing rows, or re-point them in
    this same change) has something concrete to act on.

    A provisional draft id (`frob.tickets._provisional.is_draft_id`) is
    ALWAYS clear (`()`, no scan run): `frob ticket land`'s own draft-
    finalize step (T-0811/T-0812) rewrites every `T-draft-<hex8>`
    reference -- registry dispositions and both waiver grammars alike --
    to the ticket's final id in the SAME landing commit, so a draft
    citing itself is never actually left dangling. WAIVE006/WAIVE007
    already carry the identical `T-draft-*` exemption for the same reason;
    this mirrors it rather than re-litigating the rationale.

    T-0854 rework: `base_ref` (default `"main"`) makes the exemption
    diff-aware instead of scope-based (the reviewer-rejected, gameable
    prior shape -- see the module docstring). A citation matched in the
    CURRENT tree is only reported when the exact same citation (same
    file, same text, via `_content_key`) ALSO exists at `base_ref`,
    unchanged -- proving this diff did not actually resolve it. A
    citation this diff freshly introduces (a new file/row, or one that
    replaced a different prior value) never matches anything at
    `base_ref` and is silently exempt, no scope declaration required or
    consulted. `base_ref` failing to resolve at all (a typo, or this
    function's own `"main"` default in a repo whose default branch is
    named something else) is FAIL-CLOSED, not permissive: every citation
    found in the current tree is reported unresolved rather than silently
    exempted just because "was it already there" could not be answered
    (see `_git_grep`'s own docstring for the `None`-vs-`()` distinction
    this depends on)."""
    from frob.tickets._provisional import is_draft_id

    if is_draft_id(ticket_id):
        return ()

    def _scan(revision: str | None) -> tuple[str, ...] | None:
        found: list[str] = []
        for pattern, pathspec in (
            (_registry_pattern(ticket_id), _REGISTRY_PATHSPEC),
            (_waiver_pattern(ticket_id), _WAIVER_PATHSPEC),
        ):
            result = _git_grep(root, pattern, pathspec=pathspec, revision=revision)
            if result is None:
                return None
            found.extend(_drop_escaped_mentions(result, pattern))
        return tuple(found)

    current = _scan(None)
    assert current is not None  # revision=None never returns the None sentinel
    if not current:
        return ()
    base = _scan(base_ref)
    if base is None:
        # Cannot verify whether these citations predate this diff --
        # report them all rather than silently clearing the closing/
        # landing ticket on an unanswerable question.
        return current
    base_keys = {_content_key(line) for line in base}
    return tuple(line for line in current if _content_key(line) in base_keys)


__all__ = ["live_tracker_citations"]
