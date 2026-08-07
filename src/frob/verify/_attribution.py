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
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

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


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
class AttributionError(ErrorSet):
    """Fallible outcomes of `attribute_batch`."""

    GraphUnavailable = "the reference graph could not be built/loaded for attribution"


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
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


def _resolve_symbol(snapshot, file: str, line: int | None) -> str | None:  # noqa: ANN001
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
    return frozenset(ref for ref, record in snapshot.symbols.items() if record.id.path == file)


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
    raising or returning a half-built pair."""
    from frob.graph import build_graph, build_reference_graph, load_graph

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
    call_graph = build_reference_graph(root, paths)
    return snapshot, call_graph


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
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

    results: list[Attribution] = []
    for entry in findings:
        line: int | None
        if len(entry) == 3:
            rule_id, file, line = entry
        else:
            rule_id, file = entry
            line = None
        symbol = _resolve_symbol(snapshot, file, line)
        candidates = {symbol} if symbol is not None else _symbols_in_file(snapshot, file)

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

        if len(matches) == 1:
            winner, path = matches[0]
            _log.info(
                "attribution: %s at %s%s -> commit=%s ticket=%s via %s",
                rule_id,
                file,
                f":{line}" if line is not None else "",
                winner.commit_sha[:12],
                winner.ticket_id,
                " -> ".join(path),
            )
            results.append(
                Attribution(
                    rule_id=rule_id,
                    file=file,
                    line=line,
                    symbol=symbol,
                    status="attributed",
                    commit_sha=winner.commit_sha,
                    ticket_id=winner.ticket_id,
                    reachability_path=path,
                )
            )
            continue

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
            f":{line}" if line is not None else "",
            reason,
            candidate_shas,
        )
        results.append(
            Attribution(
                rule_id=rule_id,
                file=file,
                line=line,
                symbol=symbol,
                status="unattributed",
                candidate_commits=candidate_shas,
                reason=reason,
            )
        )

    return Ok(tuple(results))


__all__ = [
    "Attribution",
    "AttributionError",
    "attribute_batch",
]
