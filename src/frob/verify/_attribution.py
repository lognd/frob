# frob:ticket T-1690
"""T-1690: symbolic attribution -- map a red batch verification's findings
back to the specific land commit that caused them (docs/modules/tickets.md).

THE RULE THIS MODULE IMPLEMENTS. A finding anchored at symbol S attributes
to the batch commit whose `VerifyQueueEntry.touched_symbols` REACHES S in
the reference graph (`frob.graph.callgraph.build_reference_graph`'s
caller-symref -> callee-symref edges). "The commit that touched the same
file" is the LEXICAL shortcut this module deliberately refuses: it is
wrong whenever a change breaks a CALLER rather than a callee, and it
misreports a pure symbol move between files as a regression the moment the
moved symbol's file changes out from under a path-keyed identity. Every
reachability decision here walks `CallGraph.calls` (symref -> symref
edges), never a path string.

AMBIGUITY IS A FIRST-CLASS OUTCOME, NOT A COIN FLIP. Exactly one candidate
commit reaching S is `attributed`; zero or more than one is
`unattributed` -- a distinct, equally-real status, never resolved by
picking the newest commit as a tiebreak (T-1686's own standing decision:
a confident wrong attribution costs more than an honest "unknown", because
it sends someone to read a diff that is not the cause). `unattributed`
findings are the bisect leaf's own input; this module does not attempt to
narrow them further.

TIER 1 (SET DIFF, upstream of this module) already yields NEW findings as
identities rather than a count (T-1684's rolling baseline,
`frob.app.ticket_runner._rapid_sweep._read_baseline`/`_write_baseline`).
This module is TIER 2: given that identity set plus the durable batch of
`VerifyQueueEntry` records the queue accumulated since the last watermark
advance, resolve each finding to a symbol and decide which commit's
touched set reaches it.

SYMBOL RESOLUTION IS BEST-EFFORT WHEN LINE INFORMATION IS ABSENT. The
existing `(rule_id, file)` finding identity `_rapid_sweep`/`_worker`
already carry does not include a line number -- widening that shape is
explicitly out of this ticket's declared scope (`_land_cmd.py`/`_verify.py`
are not in `scope`). When a finding's `line` IS known, `_resolve_symbol`
picks the single enclosing symbol from its span, exactly as designed.
When it is NOT known, this module falls back to treating every symbol
DEFINED IN that file as a candidate target -- strictly better than a bare
file-level identity comparison (a per-symbol reachability check still
runs), but honestly weaker than true line-precision: a multi-symbol file
where only one function is actually broken can widen the candidate set
enough to manufacture ambiguity that true line-precision would resolve.
This degradation is deliberate and disclosed here, not silently narrowed
into a false confidence.

"CANNOT VERIFY" IS NEVER "VERIFIED" -- extended to attribution: a graph
that cannot be built/loaded at all makes EVERY finding's attribution
impossible, and this module returns `Err(AttributionError.
GraphUnavailable)` for the whole batch rather than quietly attributing
some findings and silently skipping others."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.verify._watermark import VerifyQueueEntry

_log = get_logger(__name__)

# Same bound class as `frob.graph.affects.affects`/`callgraph.closure`
# (INV-014): a best-effort reachability walk over a real-world graph must
# be depth-limited and node-capped, or a densely cross-referenced module
# turns one attribution query into an unbounded walk. Wider than
# `affects`'s defaults on purpose -- a caller->callee call chain can be
# deeper than a `uses-contract` dependency chain in this repo's own
# call-graph shape.
_DEFAULT_MAX_DEPTH = 12
_DEFAULT_MAX_NODES = 4000

#: `.frob/cache.db` -- the same graph-snapshot cache path
#: `frob.app._snapshot.load_or_build_snapshot` resolves against, so a
#: warm cache from any other graph-backed runner is reused here too rather
#: than triggering a second cold build. Not imported from `frob.app`
#: (`frob.verify` must not import `frob.app` at module scope -- the same
#: cycle-avoidance rule `_worker._default_verify_fn`'s own deferred import
#: already documents) -- the literal is duplicated here, one line, rather
#: than pulling in the whole `frob.app` package for one `Path` constant.
_GRAPH_CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
class AttributionError(ErrorSet):
    """Fallible outcomes of `attribute_batch`."""

    GraphUnavailable = "the reference graph could not be built/loaded for attribution"


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
class Attribution(BaseModel):
    """One finding's attribution outcome: either `status="attributed"`
    (exactly one batch commit's touched symbols reach the finding's
    symbol -- `commit_sha`/`ticket_id`/`reachability_path` are all set) or
    `status="unattributed"` (zero or more than one candidate reached it --
    `candidate_commits` names every commit that DID reach it, empty for
    the zero-candidate case, so a reader can tell "nobody could have
    caused this" apart from "too many could have"). `reachability_path`
    is the actual symref chain `attribute_batch` walked from the owning
    commit's touched symbol to the finding's own symbol -- logged and
    persisted here specifically so an attribution is auditable evidence,
    never a bare assertion (T-1686's own standing constraint)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    file: str
    line: int | None = None
    #: The resolved symref, or `None` when `line` was absent and the file
    #: itself defines zero symbols the graph could resolve (an empty
    #: file, a non-source file, or a file the graph never parsed).
    symbol: str | None = None
    status: str
    commit_sha: str | None = None
    ticket_id: str | None = None
    reachability_path: tuple[str, ...] = ()
    candidate_commits: tuple[str, ...] = ()
    #: Human-readable "why unattributed" -- always empty for an attributed
    #: finding, always non-empty for an unattributed one.
    reason: str = ""


def _resolve_symbol(  # noqa: ANN001
    snapshot, file: str, line: int | None
) -> str | None:
    """The single symref in `snapshot.symbols` whose file matches `file`
    and whose `span` contains `line`, or `None` when `line` is absent or
    no symbol's span contains it. Ambiguity (two symbols somehow claiming
    the same line -- should not happen for a real `GraphSnapshot`, but
    this is a best-effort read, not a soundness guarantee) resolves to
    the FIRST match in iteration order rather than raising; a slightly
    imprecise single symbol is still strictly better input to `_reaches`
    than falling back to the whole-file candidate set unnecessarily."""
    if line is None:
        return None
    for ref, record in snapshot.symbols.items():
        if record.id.path == file and record.span[0] <= line <= record.span[1]:
            return ref
    return None


def _symbols_in_file(snapshot, file: str) -> frozenset[str]:  # noqa: ANN001
    """Every symref `snapshot.symbols` records against `file` -- the
    degraded, whole-file candidate set `_resolve_symbol` falls back to
    when `line` is unknown (see this module's own docstring, "SYMBOL
    RESOLUTION IS BEST-EFFORT...")."""
    return frozenset(
        ref for ref, record in snapshot.symbols.items() if record.id.path == file
    )

def _reaches(
    calls: Mapping[str, tuple[str, ...]],
    start: str,
    target: str,
    *,
    max_depth: int,
    max_nodes: int,
) -> tuple[str, ...] | None:
    """Bounded forward BFS from `start` over `calls` (caller -> callee
    edges): the symref path from `start` to `target` if `target` is
    reachable, else `None`. Depth-limited, node-count-capped, cycle-
    guarded (a visited set) -- the same shape `frob.graph.callgraph.
    closure`/`frob.graph.affects.affects` already establish for a
    bounded, best-effort graph walk (INV-014). `start == target` returns
    the trivial one-node path immediately: a commit that touched the
    finding's own symbol directly always reaches it, no traversal
    needed."""
    if start == target:
        return (start,)
    visited: set[str] = {start}
    parent: dict[str, str] = {}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        callees = calls.get(node, ())
        # PERF003: a membership check (`in` over `callees`, a hash lookup
        # once `calls.get` returns) is preferred over a per-item `==`
        # comparison inside this loop -- checked BEFORE the enqueue loop
        # below so the common "not reachable from this node at all" case
        # never pays for both.
        if target in callees:
            parent[target] = node
            path = [target]
            cur = target
            while cur != start:
                cur = parent[cur]
                path.append(cur)
            return tuple(reversed(path))
        for callee in callees:
            if callee in visited:
                continue
            if len(visited) >= max_nodes:
                return None
            visited.add(callee)
            parent[callee] = node
            queue.append((callee, depth + 1))
    return None


def _load_snapshot_and_call_graph(root: Path):  # noqa: ANN201
    """Load-or-build the graph snapshot (symbol identity + spans) and, over
    the SAME file set, the reference call graph (symref -> symref edges) --
    the two structures `attribute_batch` needs, built together so a caller
    never has to know the two-step shape. `build_reference_graph` (not
    `build_call_graph`) on purpose: T-0422's own broader-recall resolution
    (a symbol referenced via a dispatch table or decorator, not only a
    direct `name(...)` call token) is the more conservative choice for
    attribution -- missing a real reachability edge manufactures a false
    UNATTRIBUTED, which is the safer failure direction than `build_call_
    graph`'s narrower call-token-only recall would risk.

    Returns `None` on any build failure -- callers translate that to
    `Err(AttributionError.GraphUnavailable)` rather than this helper
    raising or returning a half-built pair.

    T-2156: uses `build_reference_graph_module_scoped`, NOT
    `build_reference_graph` -- the latter's blanket short-name resolution
    (deliberately over-inclusive for its original consumer, T-0422's
    dead-symbol gate) fabricates a reachability edge between any two
    same-named private symbols in unrelated files, which for THIS
    consumer manufactures false attributions rather than false
    UNATTRIBUTEDs. See `build_reference_graph_module_scoped`'s own
    docstring for the incident and the module/import-scoped resolution
    rule that replaces it here."""
    from frob.graph import build_graph, load_graph
    from frob.graph.callgraph import build_reference_graph_module_scoped

    cache = root / _GRAPH_CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_ok:
        snapshot = loaded.danger_ok
    else:
        built = build_graph(root, cache)
        if built.is_err:
            _log.error(
                "attribution: graph build failed for %s: %s", root, built.danger_err
            )
            return None
        snapshot = built.danger_ok
    paths = tuple(snapshot.file_hashes.keys())
    call_graph = build_reference_graph_module_scoped(root, paths)
    return snapshot, call_graph


# frob:doc docs/modules/testing.md#ad-hoc-attribution-t-2018
# frob:ticket T-2018
# frob:tests tests/unit/verify/test_attribution.py::TestLoadAttributionContext.test_returns_a_usable_snapshot_and_call_graph  # noqa: E501
def load_attribution_context(
    root: Path,
) -> Result[tuple, AttributionError]:
    """T-2018: the public seam a CALLER (e.g. `frob verify explain`)
    builds ONCE and threads through both `build_ad_hoc_batch` (needs the
    snapshot half) and `attribute_batch`'s own `graph_and_calls=`
    parameter (needs both halves) -- so a single `frob verify explain`
    invocation pays for exactly one graph load/build, never two, even
    though it now needs the graph for two different purposes (finding
    the candidate commits' touched symbols, AND resolving the finding's
    own symbol / walking reachability). Thin wrapper over `_load_
    snapshot_and_call_graph`, made public rather than reaching across
    the package boundary at a private name."""
    loaded = _load_snapshot_and_call_graph(root)
    if loaded is None:
        return Err(AttributionError.GraphUnavailable)
    return Ok(loaded)


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_caller_break_attributes_to_the_caller_commit  # noqa: E501
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_two_reaching_commits_is_unattributed  # noqa: E501
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_zero_reaching_commits_is_unattributed  # noqa: E501
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_direct_touch_attributes_at_depth_zero  # noqa: E501
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_missing_line_falls_back_to_whole_file_candidates  # noqa: E501
# frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_graph_unavailable_is_an_error_for_the_whole_batch  # noqa: E501
def attribute_batch(
    root: Path,
    findings: Iterable[tuple[str, str] | tuple[str, str, int]],
    batch: Sequence[VerifyQueueEntry],
    *,
    graph_and_calls: tuple | None = None,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_nodes: int = _DEFAULT_MAX_NODES,
) -> Result[tuple[Attribution, ...], AttributionError]:
    """Attribute every finding in `findings` (`(rule_id, file)` or
    `(rule_id, file, line)` tuples -- the exact shapes `_rapid_sweep`'s
    baseline diff already produces) against `batch` (the durable
    `VerifyQueueEntry` records the batch verification covers, oldest
    first -- typically `frob.verify.queue_status(root)`'s own return).

    For each finding: resolve its symbol (or, absent a line, its
    whole-file candidate symbol set -- see this module's own docstring),
    then check every `batch` entry's `touched_symbols` for forward
    reachability to that symbol via the reference call graph. Exactly one
    reaching commit is `attributed`; zero or more than one is
    `unattributed`, with every reaching commit's sha recorded in
    `candidate_commits` for the ambiguous case (empty for the
    zero-candidate case).

    `graph_and_calls`, when given, is an already-built `(GraphSnapshot,
    CallGraph)` pair -- lets a caller (or a test) skip the load/build step
    entirely; `None` (the default) builds/loads it here via `frob.graph`.
    Returns `Err(AttributionError.GraphUnavailable)` for the WHOLE batch
    on a build failure -- see this module's own docstring, ""CANNOT
    VERIFY" IS NEVER "VERIFIED" -- extended to attribution"."""
    if graph_and_calls is not None:
        snapshot, call_graph = graph_and_calls
    else:
        loaded = _load_snapshot_and_call_graph(root)
        if loaded is None:
            return Err(AttributionError.GraphUnavailable)
        snapshot, call_graph = loaded

    results = tuple(
        _attribute_one(
            entry, batch, snapshot, call_graph, max_depth=max_depth, max_nodes=max_nodes
        )
        for entry in findings
    )
    return Ok(results)


#: T-2018: cold-start candidate-commit window when no watermark exists yet
#: to anchor an ad-hoc attribution range on (this repo's own state at
#: T-2018's own measurement time, `frob verify status` -> `watermark:
#: (none yet)`) -- bounded the same way `_DEFAULT_MAX_DEPTH`/`_DEFAULT_
#: MAX_NODES` bound the reachability walk above: a real-world repo's
#: commit history is effectively unbounded, so an ad-hoc query with no
#: better anchor must still be a bounded, best-effort probe, not an
#: unbounded `git log`.
_DEFAULT_AD_HOC_COMMIT_LIMIT = 50

#: A `T-####`-shaped token in a commit subject line -- the same shape
#: `frob.tickets._land._directive_ticket_ids_in_diff` and this repo's own
#: commit-message convention (`docs(tickets): land T-1234 ...`) already
#: use; local here rather than imported since `_land.py`'s own version is
#: diff-body-scoped (finds directives across many lines), not a single
#: commit-subject probe.
_TICKET_ID_IN_SUBJECT = re.compile(r"T-[0-9]{4,}")


def _commit_subject(root: Path, commit_sha: str) -> str:
    """`commit_sha`'s own one-line subject, or `""` on any git failure --
    best-effort only, `build_ad_hoc_batch`'s `ticket_id` field is
    informational (which land this candidate came from), never load-
    bearing for the reachability decision itself."""
    from frob.gitio import run_argv

    spawned = run_argv(("git", "-C", str(root), "log", "-1", "--format=%s", commit_sha))
    if spawned.is_err:
        return ""
    return spawned.danger_ok.stdout.strip()


# T-2018: NOT a reimplementation of `frob.tickets._land.
# _touched_symrefs_for_intent` reached through a different import (that
# function's own home is a good one -- land-time intent recording,
# scoped to `frob.tickets`); this is the SAME span-overlap algorithm,
# duplicated locally for the identical reason `_land.py`'s own
# `frob:waive DUP001` states: a cross-package private import from
# `frob.verify` back into `frob.tickets._land` is a worse coupling than
# one small, stable, well-tested function living in each of its two
# natural homes. `attribute_batch` itself is NOT duplicated anywhere --
# this only builds its `batch` argument from a different data source.
def _touched_symrefs(diff, snapshot) -> tuple[str, ...]:  # noqa: ANN001
    """Every symbol in `snapshot` whose span overlaps a `diff` hunk in the
    same file, sorted for determinism."""
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    touched: set[str] = set()
    for record in snapshot.symbols.values():
        for span in hunks_by_file.get(record.id.path, ()):
            if span[0] <= record.span[1] and record.span[0] <= span[1]:
                touched.add(record.symref)
                break
    return tuple(sorted(touched))


# frob:doc docs/modules/testing.md#ad-hoc-attribution-t-2018
# frob:ticket T-2018
# frob:tests tests/unit/verify/test_attribution.py::TestBuildAdHocBatch.test_covers_a_commit_the_persisted_queue_never_saw  # noqa: E501
def build_ad_hoc_batch(
    root: Path,
    *,
    snapshot,  # noqa: ANN001 -- GraphSnapshot, deferred-import type (module docstring's own convention)
    since: str | None = None,
    limit: int = _DEFAULT_AD_HOC_COMMIT_LIMIT,
) -> tuple[VerifyQueueEntry, ...]:
    """T-2018: the answer to "the persisted verify queue is empty (or does
    not cover the commit I need), attribute against recent git history
    instead" -- reusing `attribute_batch` UNCHANGED, never duplicating
    its reachability logic (module docstring's own "AMBIGUITY IS A
    FIRST-CLASS OUTCOME" rule still applies to every `Attribution` this
    batch feeds into `attribute_batch`).

    For each commit sha `frob.gitio.recent_commits(root, since=since,
    limit=limit)` returns (every commit since a watermark sha when
    `since` is given, else the `limit`-bounded most recent commits on
    `HEAD` for a cold start with no watermark), computes that commit's
    own diff (`frob.gitio.commit_diff`, NOT `working_diff` -- this walks
    PAST commits, not the current working tree) and the symbols it
    touched (`_touched_symrefs`, over the SAME `snapshot` every candidate
    is checked against, so reachability from every candidate targets the
    identical symbol identity space). A commit whose diff fails to
    compute, or that touches no resolvable symbol, is silently OMITTED
    from the returned batch (logged at INFO) rather than raising --
    matching `_record_verify_intent_for_landed_commit`'s own "an
    unresolvable commit is a liability, never a reason to abort the
    whole query" posture; `profile="ad-hoc"` marks every synthesized
    entry as NOT a real recorded land intent, so a caller inspecting the
    batch (e.g. a future audit of what fed an attribution) can tell the
    two provenances apart."""
    from frob.gitio import commit_diff, recent_commits

    shas = recent_commits(root, since=since, limit=limit)
    if shas.is_err:
        _log.warning(
            "attribution: build_ad_hoc_batch: could not list commits (since=%r): %s",
            since,
            shas.danger_err,
        )
        return ()

    entries: list[VerifyQueueEntry] = []
    for sha in shas.danger_ok:
        diff = commit_diff(root, sha)
        if diff.is_err:
            _log.info(
                "attribution: build_ad_hoc_batch: %s diff unavailable (%s), omitting",
                sha[:12],
                diff.danger_err,
            )
            continue
        touched = _touched_symrefs(diff.danger_ok, snapshot)
        if not touched:
            _log.info(
                "attribution: build_ad_hoc_batch: %s touched no resolvable "
                "symbol, omitting",
                sha[:12],
            )
            continue
        subject = _commit_subject(root, sha)
        match = _TICKET_ID_IN_SUBJECT.search(subject)
        ticket_id = match.group(0) if match else "unknown"
        entries.append(
            VerifyQueueEntry(
                commit_sha=sha,
                ticket_id=ticket_id,
                touched_symbols=touched,
                enqueued_at="",
                profile="ad-hoc",
            )
        )
    _log.info(
        "attribution: build_ad_hoc_batch: %d candidate commit(s) examined, "
        "%d yielded a resolvable touched-symbol set",
        len(shas.danger_ok),
        len(entries),
    )
    return tuple(entries)


def _parse_finding(
    entry: tuple[str, str] | tuple[str, str, int],
) -> tuple[str, str, int | None]:
    """Tier 1: split one raw `(rule_id, file)`/`(rule_id, file, line)`
    finding identity into its three parts, `line` defaulting to `None`
    when absent -- the exact shapes `_rapid_sweep`'s rolling-baseline
    diff already produces."""
    if len(entry) == 3:
        rule_id, file, line = entry
        return rule_id, file, line
    rule_id, file = entry
    return rule_id, file, None


def _matching_batch_entries(
    candidates: frozenset[str],
    batch: Sequence[VerifyQueueEntry],
    call_graph,  # noqa: ANN001
    *,
    max_depth: int,
    max_nodes: int,
) -> list[tuple[VerifyQueueEntry, tuple[str, ...]]]:
    """Tier 2: THE reachability leaf. Every `batch` entry whose
    `touched_symbols` reaches at least one of `candidates` via the
    reference call graph, paired with the reachability path that proved
    it -- the rule this whole module exists to implement (a finding
    attributes to the batch commit whose touched symbols REACH it, never
    a path-string match)."""
    matches: list[tuple[VerifyQueueEntry, tuple[str, ...]]] = []
    for batch_entry in batch:
        found_path: tuple[str, ...] | None = None
        for touched in batch_entry.touched_symbols:
            for target in candidates:
                path = _reaches(
                    call_graph.calls,
                    touched,
                    target,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                )
                if path is not None:
                    found_path = path
                    break
            if found_path is not None:
                break
        if found_path is not None:
            matches.append((batch_entry, found_path))
    return matches


def _attribute_one(
    entry: tuple[str, str] | tuple[str, str, int],
    batch: Sequence[VerifyQueueEntry],
    snapshot,  # noqa: ANN001
    call_graph,  # noqa: ANN001
    *,
    max_depth: int,
    max_nodes: int,
) -> Attribution:
    """Tier 3: the ambiguity/logging bookkeeping for ONE finding, given
    its tier-2 matches -- exactly one reaching commit is `attributed`,
    zero or more than one is `unattributed`, and either way the decision
    is logged (INFO with the reachability path for an attribution,
    WARNING with every candidate for an ambiguity or a miss) so it is
    auditable, never a bare assertion."""
    rule_id, file, line = _parse_finding(entry)
    symbol = _resolve_symbol(snapshot, file, line)
    candidates = (
        frozenset({symbol}) if symbol is not None else _symbols_in_file(snapshot, file)
    )
    matches = _matching_batch_entries(
        candidates, batch, call_graph, max_depth=max_depth, max_nodes=max_nodes
    )
    loc = f":{line}" if line is not None else ""

    if len(matches) == 1:
        winner, path = matches[0]
        _log.info(
            "attribution: %s at %s%s -> commit=%s ticket=%s via %s",
            rule_id,
            file,
            loc,
            winner.commit_sha[:12],
            winner.ticket_id,
            " -> ".join(path),
        )
        return Attribution(
            rule_id=rule_id,
            file=file,
            line=line,
            symbol=symbol,
            status="attributed",
            commit_sha=winner.commit_sha,
            ticket_id=winner.ticket_id,
            reachability_path=path,
        )

    candidate_shas = tuple(m[0].commit_sha for m in matches)
    reason = (
        "no batch commit's touched symbols reach this finding"
        if not matches
        else f"{len(matches)} batch commits' touched symbols all reach this finding"
    )
    _log.warning(
        "attribution: %s at %s%s UNATTRIBUTED (%s); candidates=%s",
        rule_id,
        file,
        loc,
        reason,
        candidate_shas,
    )
    return Attribution(
        rule_id=rule_id,
        file=file,
        line=line,
        symbol=symbol,
        status="unattributed",
        candidate_commits=candidate_shas,
        reason=reason,
    )

__all__ = [
    "Attribution",
    "AttributionError",
    "attribute_batch",
    "build_ad_hoc_batch",
    "load_attribution_context",
]
