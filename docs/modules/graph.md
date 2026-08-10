# frob.graph -- obligation graph engine

One sentence: a persistent registry of every symbol's identity and digests,
plus typed edges declared in comments, so that any change to code, docs, or
contracts is detectable statically -- a type checker for obligations.

Built on `frob.lang` (tree-sitter): uniform symbol and comment extraction
for Python, TypeScript, Rust, C, and C++.

## Symbol references

<!-- frob:waive DOC006 reason="illustrative example of the path::Qualified.Name form, not a real pointer -- GraphStore.load is a made-up placeholder, not a claim that this file/symbol exists" -->
Canonical form everywhere: `path::Qualified.Name`, e.g.
`src/frob/graph/store.py::GraphStore.load`. Paths are repo-root-relative,
POSIX separators. A bare `path` refers to the whole file.

## Public API

<!-- frob:describes src/frob/lang/__init__.py::parse_file -->
<!-- frob:describes src/frob/lang/__init__.py::supported_languages -->
<!-- frob:describes src/frob/graph/__init__.py::build_graph -->
<!-- frob:describes src/frob/graph/__init__.py::load_graph -->
<!-- frob:describes src/frob/graph/__init__.py::resolve -->
<!-- frob:describes src/frob/graph/__init__.py::edges_from -->
<!-- frob:describes src/frob/graph/__init__.py::edges_to -->
<!-- frob:describes src/frob/graph/lock.py::load_lock -->
<!-- frob:describes src/frob/graph/lock.py::acknowledge -->
<!-- frob:describes src/frob/graph/lock.py::drift -->
<!-- frob:describes src/frob/graph/lock.py::write_lock -->

```python
# frob/lang/__init__.py
def parse_file(path: Path) -> Result[ParsedFile, LangError]
    # WHY: single entry point; language dispatch is internal (by extension).
def supported_languages() -> frozenset[str]

# frob/lang/_nodes.py (T-0989; re-exported unchanged from frob/lang/__init__.py
# -- import path `from frob.lang import ...` is unaffected)
def cpp_function_nodes(tree: Tree) -> tuple[tuple[Node, str], ...]
def child_by_field(node: Node, field: str) -> Node | None
def node_text(node: Node | None) -> str
def resolve_local_import(specifier: str, language: str, *, file_dir: Path,
                          root: Path) -> str | None

# frob/graph/__init__.py
def build_graph(root: Path, cache: Path) -> Result[GraphSnapshot, BuildError]
    # BuildError = GraphError | LangError. Incremental: re-parses only files
    # whose content hash changed in cache (per-file granularity, sqlite-backed).
    # Also walks docs/**/*.md for frob:describes anchors. GraphSnapshot.stats
    # (a BuildStats) reports parsed vs cache_hits for this call.
    # `frob.toml`'s `[graph] exclude = ["glob", ...]` (fnmatch, root-relative
    # POSIX paths) is additive to the built-in dir excludes (.git, .venv,
    # node_modules, target, build, dist, __pycache__, .frob); missing table
    # is `()`. Used by frob's own frob.toml to exclude tests/fixtures/**
    # so fixture symbols never create gate obligations.
def load_graph(cache: Path) -> Result[GraphSnapshot, GraphError]
    # Cache-only load for read paths; Err(CacheStale) if any on-disk file hash
    # moved since the cache was built, Err(CacheCorrupt) if the cache is
    # unreadable or has never been built (including a missing cache file).
def resolve(snapshot: GraphSnapshot, ref: str) -> Result[SymbolRecord, GraphError]
def edges_from(snapshot: GraphSnapshot, ref: str) -> tuple[Edge, ...]
def edges_to(snapshot: GraphSnapshot, target: str) -> tuple[Edge, ...]

# frob/graph/lock.py
def load_lock(path: Path) -> Result[LockFile, LockError]
    # A missing frob.lock is Ok(LockFile()) (empty), not an error -- first ack
    # creates the file. Only malformed JSON/schema is Err(Malformed).
def acknowledge(lock: LockFile, snapshot: GraphSnapshot, refs: Sequence[str],
                *, reason: str, actor: str | None = None) -> Result[LockFile, LockError]
    # Records current digests for refs; each ref must be an edge endpoint AND
    # resolve to a symbol (else Err(UnknownRef)). Facet is looked up from any
    # DESCRIBES edge targeting the ref (attrs["facet"]), default "sig".
    # T-1317: `reason` is keyword-only and REQUIRED -- Err(AckReasonMissing)
    # blank, Err(AckReasonBoilerplate) for a rubber-stamp reason. Every
    # (ref, facet) actually (re-)acked appends one AckAuditEntry to the
    # returned LockFile's `ack_log` (old_digest/new_digest/reason/actor/at)
    # -- see "Ack accountability (T-1317)" in docs/modules/gates.md.
def drift(lock: LockFile, snapshot: GraphSnapshot) -> DriftReport
    # Pure comparison; never fails. Dangling edges and stale acks.
def write_lock(lock: LockFile, path: Path) -> Result[Unit, LockError]
    # Atomic (temp + os.replace). Deterministic: entries sorted by (ref,
    # facet), indent=2, trailing newline; `ack_log` is written in its
    # existing append (chronological) order, never resorted (T-1317).
```

## Affects

T-0325, the north-star query.

<!-- frob:describes src/frob/graph/affects.py::AffectedSet -->
<!-- frob:describes src/frob/graph/affects.py::affects -->

"If X's digest changed, exactly WHICH documentation and WHICH other code
must be reviewed/updated" -- answered warm, from an already-built
`GraphSnapshot`, without running a single test (CLAUDE.md's north-star
vision: a static type-checker for docs). `frob_doc_for` (`frob.serve`)
already answers the direct, one-hop question for a single symbol; `affects`
extends it to the transitive case a real contract change has.

```python
# frob/graph/affects.py
class AffectedSet(BaseModel):
    root: str
    dependents: tuple[str, ...]   # transitively uses-contract-dependent symrefs
    docs: tuple[str, ...]         # doc anchors covering root or any dependent
    tests: tuple[str, ...]        # frob:tests symrefs covering root or any dependent
    truncated: bool               # max_depth/max_nodes cut the walk short

def affects(snapshot: GraphSnapshot, ref: str, *,
            max_depth: int = 8, max_nodes: int = 500) -> AffectedSet
```

- **Edge types that feed the digest**: `uses-contract` (reverse-walked --
  a dependent's `frob:uses-contract ref` directive means `ref`'s signature
  change propagates to the dependent) drives the transitive symbol closure;
  `doc` and `describes` (both directions, same pair `frob_doc_for` reads)
  and `tests` are collected at every node the closure visits, not just at
  `ref` itself.
- **Depth/transitivity semantics**: bounded BFS, depth-limited and
  node-count-capped, cycle-guarded via a visited set -- the same posture as
  `frob.graph.callgraph.closure` (INV-014). `truncated=True` means the
  bound cut the dependent walk short; the doc/test sets are still exact for
  every node actually visited.
- **Query surface**: the MCP tool `frob_affects(symref, max_depth=None,
  max_nodes=None)` (`frob.serve`), backed by the warm graph snapshot
  `frob.serve._warm._warm_state` already builds -- no cold reload, no test
  run. `frob graph affects <ref> [path] [--json] [--max-depth N]
  [--max-nodes N]` (T-0628, `src/frob/app/graph_runner.py`) is the CLI
  counterpart T-0325 cut as out of scope -- prints the same
  dependents/docs/tests, `[TRUNCATED]` flagged up front in human mode.
- **Enforcement**: `frob.gates.affect_drift_gate` (AFFECT001/AFFECT002,
  T-0628, `src/frob/gates/__init__.py`) is the digest-drift gate this query
  was always meant to feed -- wired into `frob check` as the `affect_drift`
  gate name (`gates-fast` stage group). For every symbol the working diff
  touches, it walks that symbol's `affects()` closure and FAILS when a
  dependent doc anchor (AFFECT001) or dependent symbol's file (AFFECT002)
  was not ALSO touched in the same diff -- the enforcement half of the
  CLAUDE.md north-star this module's docstring describes. A symbol with an
  empty closure (no `uses-contract` dependents, no doc/test edges) is
  silent; a truncated closure is checked against whatever it did visit
  (under-reports, never false-positives).

## Scope closure (T-0998)

<!-- frob:describes src/frob/graph/affects.py::ScopeClosureGap -->
<!-- frob:describes src/frob/graph/affects.py::scope_doc_code_gaps -->
<!-- frob:describes src/frob/graph/affects.py::scope_test_gaps -->
<!-- frob:describes src/frob/graph/callgraph.py::PrivateHelperGap -->
<!-- frob:describes src/frob/graph/callgraph.py::scope_private_helper_gaps -->

Moves the AFFECT001/002 idea from diff-time to scope-DECLARATION time: a
scope containing code whose `frob:doc`/`frob:describes` targets are absent
is under-captured, and the reverse (a doc in scope without its described
code) is too -- surfaced when the scope is declared/validated, not
discovered reactively mid-ticket the first time `frob check` runs
AFFECT001/COV002 against it. The closure is a TRIPLE: code<->docs,
code<->tests (a scoped code edit with no covering `frob:tests` test file
scoped is exactly the reactive scope-add churn this feature exists to
close), plus the private-helper capture below.

Three pure functions, all reusing existing traversal engines rather than
building a second one:

```python
# frob/graph/affects.py
def scope_doc_code_gaps(snapshot: GraphSnapshot, scope) -> tuple[ScopeClosureGap, ...]
def scope_test_gaps(snapshot: GraphSnapshot, scope) -> tuple[ScopeClosureGap, ...]
```

`scope_doc_code_gaps` walks the SAME `frob:doc`/`frob:describes` edges
`affects()`'s `_doc_targets_for` already reads. `direction=
"code_missing_doc"`: a scoped code symbol whose doc target file is not in
scope. `direction="doc_missing_code"`: a scoped doc anchor whose described
code file is not in scope. `scope_test_gaps` is the symmetric code<->tests
counterpart over the SAME `EdgeKind.TESTS` edges `_test_refs_for` already
reads: `direction="code_missing_test"` (scoped code, unscoped covering
test file) and `direction="test_missing_code"` (scoped test, unscoped
covered code file). Each `ScopeClosureGap` names `scoped_site` (the thing
already in scope), `target` (the other side of the edge), and
`missing_file` (the file to add).

```python
# frob/graph/callgraph.py
def scope_private_helper_gaps(root: Path, scope, files: Sequence[str]) -> tuple[PrivateHelperGap, ...]
```

Builds `build_call_graph`'s private-callee graph (the SAME substrate
`frob.dup`'s helper-inline triage and `closure` use) over `files` narrowed
to scope-adjacent directories, then flags every scoped caller's edge to a
private helper defined OUTSIDE scope as probable under-capture.
`only_used_by_scope=True` when every other observed caller of that helper
is also in scope -- the strong "just add this file" case, versus
`only_used_by_scope=False` ("review the dependency", since some other
in-scope-or-not caller also depends on it).

- **Enforcement**: `frob.gates._scope002_violations` (SCOPE002,
  WARN-only turn-on per the T-0756 new-gate-rule promotion playbook, see
  docs/modules/gates.md#scope002-t-0998) wires all three functions into
  the existing `scope` gate stage (`scope_gate`, alongside SCOPE001) --
  runs for every ticket `frob check --ticket T-XXXX`/`frob check` resolves
  an active ticket for.
- **CLI surface**: `frob ticket new`/`frob ticket scope` (`frob.app.
  ticket_runner._scope_closure_warnings`) render the identical closure
  gaps as plain warning lines right after the scope is created/changed --
  suggest-or-warn, before a `frob check` run is even needed.
- **Bounds**: `scope_doc_code_gaps` is snapshot-only (no IO); the WARN
  posture never blocks a ticket that legitimately wants a narrower scope
  than its own doc/call graph suggests.

## Call graph

<!-- frob:describes src/frob/graph/callgraph.py::CallGraph -->
<!-- frob:describes src/frob/graph/callgraph.py::build_call_graph -->
<!-- frob:describes src/frob/graph/callgraph.py::closure -->

`frob.graph.callgraph` is a SEPARATE, reusable substrate from the obligation
graph above -- caller-symref to callee-symref edges resolved from
`frob.lang.RawSymbol.body_tokens` (best-effort, name-based call scanning),
not from comment directives. Built once so more than one consumer can share
it (T-0288's dup helper-inlining triage today; T-0290's recursion detection
is the next planned consumer) rather than each re-deriving call resolution.

- `build_call_graph(root, paths, *, mark_unresolved=False)` -- parses every
  file in `paths` (typically one package/directory) and records an edge
  for every call resolved to a PRIVATE (leading-underscore) or same-file
  callee. A call to a PUBLIC symbol is never recorded as an edge at all --
  that is what makes `closure` stop at the public-API boundary for free,
  with no separate bookkeeping. T-0809: `mark_unresolved=True` (opt-in --
  see below for why the default stayed `False`) makes a call target that
  LOOKS like it should resolve under this module's own private-symbol
  convention (leading underscore) but matches zero candidates anywhere in
  `paths` get a `UNRESOLVED_CALLEE` edge instead of being silently
  dropped -- this is the real callee-resolution wiring the T-0745 protocol
  summary engine's poisoning channel needed to mean anything on a real
  scan, not just a hand-fabricated fixture `CallGraph`. A call to a name
  with no leading underscore (never looked local in the first place -- a
  builtin, stdlib, or third-party call) stays a silent omission either
  way; `build_reference_graph` always passes `mark_unresolved=False` (its
  broader "referenced anywhere" recall has no poisoning consumer to feed).

  **Why the default is `False`, not `True`**: `frob.gates` (three call
  sites, including `_cov006_third_file_reachable`) and
  `frob.dup._pipeline` already call `build_call_graph` and feed its
  output -- including `closure()` over it -- through code that assumes
  every returned entry is a real `path::qualname` symref splittable on
  `"::"`. A bare `UNRESOLVED_CALLEE` sentinel breaks that assumption
  (observed directly: an `IndexError` in `_cov006_third_file_reachable`
  during this ticket's own gate verification pass). Those call sites are
  outside this ticket's scope (`src/frob/gates/**`, `src/frob/dup/**`) to
  widen for `UNRESOLVED_CALLEE`-awareness, so the mechanism is opt-in: a
  future real production wiring of `build_call_graph` into
  `compute_protocol_summaries` passes `mark_unresolved=True` explicitly.

  **T-0813 (the real wiring)**: `frob.gates._protocol_summary
  .protocol_summary_gate` (docs/modules/gates.md#proto001-t-0813) is that
  production caller -- `PROTO001`, wired into `frob check` (the
  `protocol_summary` gate name). It also disposes of the dominant
  real-repo false-positive class `mark_unresolved=True` surfaces on
  actual code: `obj._method(...)`/`super().__init__(...)` attribute calls
  on a non-`self` receiver look like this module's private-symbol
  convention but are never a call this graph could resolve --
  `_unresolved_exempt_names` filters them out of the poisoning trigger
  (see the gates doc's PROTO001 section for the exact rule).

  <!-- frob:invariant INV-014 -->
- `closure(graph, start, *, max_depth, max_nodes)` -- bounded BFS from
  `start`: depth-limited, node-count-capped, cycle-guarded (a visited set
  handles mutual recursion), breadth-first order. Returns the reachable
  private-callee symrefs, `start` excluded.

Resolution is best-effort (flat token stream, no scope/overload
disambiguation) -- a triage aid, matching the rest of `frob.dup`'s posture,
not a soundness guarantee.

## Import graph

<!-- frob:describes src/frob/graph/imports.py::ImportGraph -->
<!-- frob:describes src/frob/graph/imports.py::UnresolvedImport -->
<!-- frob:describes src/frob/graph/imports.py::build_import_graph -->

`frob.graph.imports` (T-1985) is the file-level RESOLVED-import edge
substrate REF001 needs to stop deciding inbound references from text
mentions (T-1665, blocked on this ticket) -- answers "does file Y import
module X, resolved to a real tracked file", which no facility in
`frob.graph`/`frob.lang` answered before this: `EdgeKind` only models
`frob:`-directive edges, and `callgraph` (above) deliberately excludes
public/exported symbols and resolves CALLS, not imports.

**Python only, v1** -- every other language `frob.lang` parses (Rust, C,
C++, TypeScript, Kotlin, Strata) is disclosed out of scope: a non-`.py`
file contributes one `UnresolvedImport(reason="unsupported-language")`
per file, never a silent zero. Uses the stdlib `ast` module directly
(not `frob.lang`'s tree-sitter walkers -- `RawSymbol` has no import-
statement extraction today), which finds every import statement
regardless of nesting (`if`/`try`/`TYPE_CHECKING` guards included) and
never confuses a look-alike string for a real import.

- `build_import_graph(root, paths)` -> `ImportGraph` -- `edges[importer]`
  is every tracked file `importer` resolves an import to (deduplicated,
  sorted). `from X import Y` resolves to the submodule `X.Y` when that is
  itself a tracked file (e.g. `from . import submodule` inside a
  package's own `__init__.py`), else falls back to resolving `X` itself
  (`Y` is an attribute defined inside `X` -- only `frob.lang`-level
  symbol resolution, out of scope here, could tell those apart further).
  A star-import (`from X import *`) always resolves `X` the same way.
- `UnresolvedImport` (T-1664's UNRESOLVED posture, not `frob.gates.
  Severity` itself -- `frob.gates` depends on `frob.graph`, never the
  reverse, so importing it here would be circular) -- never a silent
  drop, for every case this module KNOWS it cannot resolve: a dynamic
  import (`importlib.import_module(...)`, bare `__import__(...)`), a
  relative import whose `level` walks above the tracked root, a file
  that fails to parse (`SyntaxError`), or a non-Python file.
- `ImportGraph.external_count` -- imports that are syntactically real but
  name something outside the tracked file set (stdlib/third-party, e.g.
  `import os`) -- reported for measurement transparency only, never
  folded into either the resolved or the unresolved tally (a fully-
  answered "not in this substrate's domain" case, not an unknown).

Measured on this repo's own `src/frob` tree (630 tracked files, 531
Python): 2522 resolved import edges across 479 files, 2480 external
(stdlib/third-party) import statements, 110 `UnresolvedImport` records
(99 non-Python files, 11 dynamic-import call sites) -- 0
`relative-import-above-root`, 0 `parse-error` on this repo's own
currently-valid tree.

REF001's own narrowing onto this substrate is T-1665, not this ticket --
this module intentionally does not change `frob.gates._refs` at all.

## Rust core

<!-- frob:describes src/frob/graph/_core.py::resolve_call_edges_native -->

T-0930: `frob.graph._core` mirrors `frob.dup._core`'s `core_available()`-
gated shim pattern (docs/modules/dup.md#rust-core) over one `frob_core`
native kernel: `resolve_call_edges` (frob-core/src/lib.rs), the batched
caller->callee matching loop `_resolve_edges` splits its per-caller
name/exempt-list extraction from (docs/audits/check-performance.md
rust-candidate row 8, `dead_symbols`' hot path).

`_resolve_edges` does NOT call this native path by default -- a real
before/after benchmark on this repo's own `src/frob/gates` package (46
packages, `dead_symbols`' actual production call site) measured it net
SLOWER end-to-end (0.164s vs 0.127s median in-scope `thread_time`) than
staying pure-Python: at this repo's real per-package data scale, PyO3's
marshaling cost for the whole `by_name` index and per-caller name lists
crossing into Rust and the result dict crossing back outweighs the
matching loop's own (already small) pure-Python cost. `resolve_call_
edges_native` stays available and parity-tested
(`tests/test_graph.py::TestResolveCallEdgesNative`) against
`_resolve_edges_python` for a future caller batching a genuinely large
single input (e.g. a whole-repo call graph in one call) where the fixed
marshaling cost would amortize over enough matching work to win.

`frob_core` additionally exports `called_names`, `ordered_called_names`,
`referenced_names`, and `unresolved_exempt_names` -- native ports of
`frob.graph.callgraph`'s per-symbol token-scan helpers, also prototyped
and benchmarked this same pass. NOT wired at all (no Python shim calls
them): each is invoked once PER SYMBOL in real use (thousands of calls
over a real package), a granularity where PyO3 per-call overhead
dominated any loop-speed win even more decisively than the batched
`resolve_call_edges` case above. Kept in `frob_core` (tested,
documented) as parked kernels, not wired -- see
`frob.graph.callgraph._ordered_called_names`'s docstring for the full
disposition.

## Protocol summary engine

<!-- frob:describes src/frob/graph/summary.py::compute_protocol_summaries -->
<!-- frob:describes src/frob/graph/summary.py::FunctionSummary -->
<!-- frob:describes src/frob/graph/summary.py::SCCTimeout -->
<!-- frob:describes src/frob/graph/summary.py::SummaryResult -->
<!-- frob:describes src/frob/graph/callgraph.py::UNRESOLVED_CALLEE -->

`frob.graph.summary` (T-0745, child 2 of the T-0739 typestate umbrella) is
a shared, bottom-up FIXPOINT engine over a `CallGraph` (above): it
summarizes every reachable function's transitive contribution to the
T-0744 protocol DSL (`frob:protocol`/`frob:transition`/`frob:requires`,
`EdgeKind.PROTOCOL`/`TRANSITION`/`REQUIRES`) -- which protocol states it
REQUIRES and which state TRANSITIONS it may perform, folding in everything
it calls, transitively, including through recursion.

- `compute_protocol_summaries(callgraph, edges, entrypoints, *,
  max_iterations=100)` -- decomposes `callgraph` into strongly-connected
  components (a private, iterative Tarjan implementation -- deliberately
  not `frob.cycle.graph.find_cycles`, which drops non-cyclic singleton
  components this engine still needs a node for) and processes them
  bottom-up: a callee's summary is always finalized before its caller's.
  A single-node, non-self-recursive component is one join pass; a
  recursive cluster (mutual recursion, or a function calling itself)
  iterates the join to a fixpoint, bounded by `max_iterations`.
- `FunctionSummary` -- one function's `requires`/`transitions` string sets
  (`"proto:state"` / `"proto:from->to"`), plus `poisoned`/`poison_reason`.
  T-0809: also `acquired`/`released`/`escaped` -- plain resource-name
  string sets (the resource-tracking DSL below), joined transitively the
  same way `requires`/`transitions` are.
- `UNRESOLVED_CALLEE` -- the sentinel callee symref a caller wires into
  `CallGraph.calls` to mean "this call site could not be bound". T-0809:
  now RE-EXPORTED from `frob.graph.callgraph` (defined there, since
  `callgraph.build_call_graph` is the real producer as of T-0809's
  `mark_unresolved` parameter) -- `frob.graph.summary.UNRESOLVED_CALLEE`
  still works unchanged for existing callers, it is the same object, not
  a second sentinel string.
- `SummaryResult` -- `summaries` (reachable functions only), plus two
  loud-failure channels the NO-FAIL-SILENT mandate requires: `not_analyzed`
  (functions no `entrypoints` member ever transitively calls -- these get
  no summary at all rather than a falsely-clean empty one) and `timeouts`
  (`SCCTimeout` -- a recursive cluster that failed to converge within
  `max_iterations`, every one of its members poisoned as a result).

Poisoning is monotone and propagates: any callee that is `UNRESOLVED_CALLEE`
or itself poisoned makes every transitive caller poisoned too, with a
`poison_reason` naming where it started. `frob.graph.summary` performs no
filesystem walk or repo scan of its own -- callers (or tests) build the
`CallGraph`/`Edge` inputs explicitly, keeping the engine itself pure and
deterministic.

### Resource-tracking DSL (T-0809)

`frob:acquire <resource>` / `frob:release <resource>` / `frob:escapes
<resource>` -- bare-target directives (same grammar shape as `frob:doc`/
`frob:ticket`, no required attributes) declaring that the enclosing
function directly acquires, releases, or transfers-out-unreleased
("escapes", e.g. returns or stores) a named resource (`fd`, `lock`,
`conn`, any opaque string). Parsed into `EdgeKind.ACQUIRE`/`RELEASE`/
`ESCAPES` edges by `frob.graph.dsl.parse_directives`, exactly like the
T-0744 protocol verbs, and folded into `FunctionSummary.acquired`/
`released`/`escaped` by `compute_protocol_summaries` via plain transitive
set union -- the same lattice-join treatment `requires`/`transitions`
already get, not a net-held/leaked computation.

This is the DSL SURFACE only. Real cleanup-obligation VERIFICATION (does
every acquire actually get released -- or legitimately escape -- on every
exit path, including exceptional ones) is PROTO005
(docs/modules/gates.md#proto005-t-0747, child 4 of the T-0739 umbrella) --
`compute_protocol_summaries` itself still only exposes the raw transitive
sets; PROTO005 does not consume them at all (it needs per-exit ordering
this fixpoint's transitive-union shape cannot give), instead running its
own intraprocedural walk directly over the DSL's `ACQUIRE`/`RELEASE`/
`ESCAPES` edges and each acquiring function's own `NormalizedFunction`
body, per that gate's own docstring.

Deferred out of this ticket's scope (see T-0809's Done report): the
T-0686 may-raise engine this substrate is meant to eventually share with
(may-raise has no implementation to consume it) -- the T-0745 DESIGN
CONSTRAINT ("one engine, whichever builds first hosts it") could not be
coordinated on this pass either, unchanged from T-0745's own disclosure.
No open ticket currently tracks building the may-raise engine -- this is
a disclosed scope cut, not active work.

T-0972: `affects`'s own `sorted(_dependents_of(snapshot, node))` BFS-walk
call picked up a reasoned `frob:waive PERF004` (the dependents set
differs per node, nothing to hoist) -- no behavior change. `acknowledge`
(`frob.graph.lock`) similarly picked up a reasoned `frob:waive PERF004`
on its own per-ref `sorted(_facets_for_ref(...))` call.

## Comment DSL

<!-- frob:describes src/frob/graph/dsl.py::parse_directives -->
<!-- frob:describes src/frob/graph/dsl.py::markdown_anchors -->

- `parse_directives` -- extracts every `frob:` directive comment in a
  parsed file into typed `Edge`s (or `MalformedDirective`s when a line
  fails to parse).
- `markdown_anchors` -- extracts `describes`-verb HTML-comment anchors
  (`frob:describes <symref> [facet]`) from a markdown doc, binding each to
  the nearest preceding heading slug.

Directives live in ordinary comments in any supported language (`#`, `//`,
`/* */`). Grammar: `frob:<verb> <target> [key="value" ...]`. One directive
per comment line. A directive binds to the innermost enclosing symbol (or
the symbol immediately following it, for preceding-line comments).

A directive line ending in a trailing backslash (`\`) continues onto the
next physical comment line -- folded before parsing, joined with the empty
string, reported at the FIRST physical line's number (T-0286); see
`docs/guides/extending/comment-dsl-directives.md#multi-line-directives-backslash-continuation`
for the full mechanics (dangling-backslash and CRLF handling included).

| Directive | Meaning (edge created) |
|---|---|
| `frob:doc docs/modules/graph.md#lock` | enclosing symbol is described by that doc anchor |
| `frob:uses-contract <symref>` | enclosing symbol depends on target's signature semantics; target sig change flags this symbol |
| `frob:invariant INV-007` | enclosing symbol is an anchor for that invariant |
| `frob:ticket T-0042` | enclosing symbol (or hunk) satisfies that ticket |
| `frob:todo T-0043 [note]` | deferred work bound to an open ticket |
| `frob:waive RULE-ID reason="..."` | suppress one gate rule here; reason required |
| `frob:tests <symref>` | enclosing test function unit-tests that symbol |
| `frob:tests <pkg-path> kind="integration"` | enclosing test exercises that package's public boundary with real collaborators |
| `frob:tests <system-id> kind="e2e"` | enclosing test drives that declared system end to end |
| `frob:decision AD-###` | enclosing symbol implements that decision record (see docs/modules/decisions.md) |
| `frob:debt RULE reason="..." ticket="T-####" [until="..."]` | a temporary, ticket-bound waiver of RULE at this site (T-0412) |
| `frob:deprecated SINCE sunset="YYYY-MM-DD" ticket="T-####" [reason="..."]` | a still-callable public symbol with a ticket-bound sunset date (T-0576) |
| `frob:channel <id>` | enclosing symbol binds to that strata Flow construct (T-0080) |
| `frob:boundary <id>` | enclosing symbol binds to that strata Boundary construct (T-0080) |
| `frob:secret <id>` | enclosing symbol binds to that strata secret-clearance construct (T-0080) |
| `frob:enforces <concept-id>` | enclosing rule/detector declares which registry concept it enforces (T-0428) |
| `frob:protocol ...` | typestate protocol declaration surface (T-0744) |
| `frob:transition ...` | typestate transition declaration (T-0744) |
| `frob:requires ...` | typestate precondition declaration (T-0744) |
| `frob:acquire <resource>` | enclosing function acquires that resource (T-0809) |
| `frob:release <resource>` | enclosing function releases that resource (T-0809) |
| `frob:escapes <resource>` | enclosing function transfers an unreleased resource out to its caller (T-0809) |
| `frob:enumerates <doc-anchor>` | enclosing collection-literal symbol is member-list-verified at that doc anchor (T-1227) |
| `frob:until <T-####>` | enclosing (code-side) or nearest-heading (markdown-side) span's negative-existence claim is bound to that ticket (T-1229) |

`frob:enumerates <symref> members="a,b,c"` (T-1227) is the markdown-side
counterpart: same HTML-comment anchor shape as `frob:describes`, but the
mandatory `members=` attribute carries the doc author's claimed member
list, AST-diffed against the collection literal's real members every
check run (DOCENUM001, docs/modules/gates.md#docenum001-t-1227).

`<!-- frob:until T-#### -->` (T-1229) is the markdown-side form of
`frob:until`: an HTML comment binding the doc section under the nearest
heading to the ticket that will build the not-yet-built thing the section
describes. `markdown_anchors` also heuristically detects negative-
existence prose itself (the "X is missing today" phrasings
`_NEGEXIST_PHRASE_RE` matches: "does not [yet] exist", "not-yet built/
implemented/wired/supported/available/shipped/landed") in the same pass
and emits a `CLAIMS_ABSENCE` edge sharing the section's anchor --
NEGEXIST001 (docs/modules/gates.md#negexist001-gate-t-1229) flags a claim
with no `frob:until` at all, or one whose bound ticket(s) already closed.

Markdown side (doc anchors), in HTML comments; applies from the comment to
the next heading of equal or higher level:

```markdown
<!-- frob:describes src/frob/graph/lock.py::acknowledge -->
<!-- frob:describes src/frob/graph/_models.py::LockFile sig -->
```

The optional trailing facet (`sig` | `body` | `doc`) selects which digest the
ack tracks; default is `sig` (docs usually describe contracts, and body-only
changes should not invalidate them).

Targets are stored as opaque strings. Graph does not validate that a ticket
or doc anchor exists -- that join is `frob.gates`' job (prevents a
graph -> tickets dependency cycle).

## Digests

Three per symbol, all sha256 over a normalized rendering of the tree-sitter
subtree (whitespace- and formatting-insensitive):

- `sig`: name, parameters, types, return type, visibility, decorators.
- `body`: implementation subtree, comments and docstrings stripped.
- `doc`: the symbol's own docstring/doc-comment, whitespace-collapsed.

<!-- frob:describes src/frob/graph/digest.py::_digest_sig -->
<!-- frob:describes src/frob/graph/digest.py::_digest_body -->
<!-- frob:describes src/frob/graph/digest.py::_digest_doc -->
<!-- frob:describes src/frob/graph/digest.py::compute_digests -->

- `_digest_sig` -- the `sig` facet's hash: hashes a symbol's normalized
  signature token stream.
- `_digest_body` -- the `body` facet's hash: hashes a symbol's normalized
  implementation token stream (empty for class/const/type).
- `_digest_doc` -- the `doc` facet's hash: hashes a symbol's collapsed
  docstring text.
- `compute_digests` -- convenience wrapper computing all three facets for
  one symbol in a single `Digests` value.

## Data models

All pydantic `BaseModel`, `frozen=True`.

<!-- frob:describes src/frob/graph/_models.py::SymbolId -->
<!-- frob:describes src/frob/graph/_models.py::Digests -->
<!-- frob:describes src/frob/graph/_models.py::SymbolRecord -->
<!-- frob:describes src/frob/graph/_models.py::SymbolRecord.symref -->
<!-- frob:describes src/frob/graph/_models.py::EdgeKind -->
<!-- frob:describes src/frob/graph/_models.py::Edge -->
<!-- frob:describes src/frob/graph/_models.py::MalformedDirective -->
<!-- frob:describes src/frob/graph/_models.py::BuildStats -->
<!-- frob:describes src/frob/graph/_models.py::GraphSnapshot -->
<!-- frob:describes src/frob/graph/_models.py::LockEntry -->
<!-- frob:describes src/frob/graph/_models.py::LockFile -->
<!-- frob:describes src/frob/graph/_models.py::AckAuditEntry -->
<!-- frob:describes src/frob/graph/_models.py::StaleItem -->
<!-- frob:describes src/frob/graph/_models.py::DanglingEdge -->
<!-- frob:describes src/frob/graph/_models.py::DriftReport -->

- `SymbolId` -- a symbol's identity: repo-relative path plus dotted
  qualname, rendered as the canonical `path::qualname` symref.
- `Digests` -- the three independent sha256 digests (`sig`/`body`/`doc`)
  tracked per symbol.
- `SymbolRecord` -- one resolvable symbol: identity, kind, publicness,
  digests, and source span.
- `SymbolRecord.symref` -- the canonical `path::qualname` string key a
  record is stored under in `GraphSnapshot.symbols`.
<!-- frob:enumerates src/frob/graph/_models.py::EdgeKind members="DOC,USES_CONTRACT,INVARIANT,TICKET,TODO,WAIVE,DEBT,DESCRIBES,TESTS,DECISION,CHANNEL,BOUNDARY,SECRET,ENFORCES,DEPRECATED,PROTOCOL,TRANSITION,REQUIRES,ACQUIRE,RELEASE,ESCAPES,ENUMERATES,UNTIL,CLAIMS_ABSENCE" -->
- `EdgeKind` -- the closed set of typed relationships a `frob:` directive
  or doc anchor can declare (24 members: doc, uses-contract, invariant,
  ticket, todo, waive, debt, describes, tests, decision, channel,
  boundary, secret, enforces, deprecated, protocol, transition, requires,
  acquire, release, escapes, enumerates, until, claims-absence -- T-1227,
  until/claims-absence T-1229).
- `Edge` -- one directive/anchor's declared obligation between a src
  symbol/doc anchor and an opaque target.
- `MalformedDirective` -- a `frob:` comment line that failed to parse,
  kept as data so nothing is silently dropped.
- `BuildStats` -- per-`build_graph` counters (parsed vs cache-hit files)
  proving incrementality to callers and tests.
- `GraphSnapshot` -- the whole obligation graph at one point in time:
  symbols, edges, malformed directives, and file hashes.
- `LockEntry` -- one acknowledged `(ref, facet)` pair and the digest it
  was acked at.
- `LockFile` -- the full `frob.lock` document: a version tag, sorted
  entries, and the append-only `ack_log` audit trail (`AckAuditEntry`,
  T-1317 -- see "Ack accountability (T-1317)" in docs/modules/gates.md).
- `AckAuditEntry` -- one append-only `frob ack` audit line (T-1317): the
  `(ref, facet)` acked, the digest delta (`old_digest`/`new_digest`),
  `reason`, `actor`, and `at`.
- `StaleItem` -- a locked entry whose current digest no longer matches
  the ack (drift).
- `DanglingEdge` -- an edge whose endpoint no longer resolves in the
  current snapshot, with rename candidates.
- `DriftReport` -- the pure comparison result between a `LockFile` and a
  `GraphSnapshot`: stale acks plus dangling edges.

```python
class SymbolId(BaseModel):      # path + qualname; renders as "path::qualname"
    path: str
    qualname: str

class Digests(BaseModel):
    sig: str
    body: str
    doc: str

class SymbolRecord(BaseModel):
    id: SymbolId
    kind: SymbolKind            # enum: function, method, class, const, type
    public: bool
    digests: Digests
    span: tuple[int, int]       # 1-based start/end lines

class EdgeKind(StrEnum):
    DOC = "doc"; USES_CONTRACT = "uses-contract"; INVARIANT = "invariant"
    TICKET = "ticket"; TODO = "todo"; WAIVE = "waive"; DESCRIBES = "describes"
    TESTS = "tests"             # attrs["kind"]: unit (default) | integration | e2e

class Edge(BaseModel):
    src: str                    # symref or doc anchor ("docs/x.md#h")
    kind: EdgeKind
    target: str                 # opaque: symref, ticket id, rule id, anchor
    origin: str                 # "file:line" of the directive
    attrs: Mapping[str, str]    # reason=..., facet=...

class BuildStats(BaseModel):            # per-build_graph() counters
    parsed: int                          # files re-parsed this call
    cache_hits: int                      # files loaded from cache unchanged

class MalformedDirective(BaseModel):    # a frob: comment line that failed to parse
    file: str
    line: int
    reason: str

class GraphSnapshot(BaseModel):
    root: str
    symbols: Mapping[str, SymbolRecord]   # keyed by symref
    edges: tuple[Edge, ...]
    malformed: tuple[MalformedDirective, ...]  # never silently dropped
    file_hashes: Mapping[str, str]        # incremental rebuild support
    stats: BuildStats                     # parsed/cache_hits for this build_graph() call

class LockEntry(BaseModel):
    ref: str
    facet: str                  # "sig" | "body" | "doc"
    digest: str

class AckAuditEntry(BaseModel):   # T-1317, append-only
    ref: str
    facet: str
    old_digest: str | None        # None only for a genuine first-ever ack
    new_digest: str
    reason: str
    actor: str
    at: date

class LockFile(BaseModel):
    version: int
    entries: tuple[LockEntry, ...]
    ack_log: tuple[AckAuditEntry, ...]   # T-1317

class StaleItem(BaseModel):     # digest moved since last ack
    entry: LockEntry
    current: str
    dependents: tuple[str, ...]  # edges whose validity this breaks

class DanglingEdge(BaseModel):  # endpoint no longer resolves
    edge: Edge
    candidates: tuple[str, ...]  # rename suggestions via body-digest match

class DriftReport(BaseModel):
    stale: tuple[StaleItem, ...]
    dangling: tuple[DanglingEdge, ...]

class ParsedFile(BaseModel):    # frob.lang output
    path: str
    language: str
    symbols: tuple[RawSymbol, ...]
    comments: tuple[RawComment, ...]
    content_hash: str
```

## Error types

<!-- frob:describes src/frob/graph/__init__.py::GraphError -->
<!-- frob:describes src/frob/graph/lock.py::LockError -->

- `GraphError` -- failure values graph read paths (`load_graph`,
  `resolve`, `edges_from`/`edges_to`) can return; never a bare exception.
- `LockError` -- failure values `frob.lock` read/write paths (`load_lock`,
  `acknowledge`, `write_lock`) can return.

```python
class LangError(ErrorSet):
    UnsupportedLanguage    = "File extension has no registered grammar"
    ParseFailed            = "tree-sitter could not produce a usable tree"
    IoFailed               = "File could not be read"
    NativeParserUnavailable = "strata-core native extension unavailable in this install (T-0133)"
    FileTooLarge           = "File exceeds the max parseable size (T-0893)"
    ParseTimedOut          = "Parse did not finish inside the wall-clock budget (T-0893)"

class GraphError(ErrorSet):
    CacheCorrupt    = "Cache file unreadable; delete .frob/cache.db to rebuild"
    CacheStale      = "Cache does not match working tree; run build_graph"
    CacheLocked     = "Cache lock held by another process; retry the command"
    UnknownSymbol   = "Symbol reference does not resolve"
    AmbiguousSymbol = "Reference matches more than one symbol"
# plus LangError via composition: BuildError = GraphError | LangError

class LockError(ErrorSet):
    Malformed          = "frob.lock could not be parsed"
    UnknownRef         = "Acknowledged ref is not an edge endpoint in the graph"
    WriteFailed        = "Atomic write of frob.lock failed"
    AckReasonMissing     = "frob ack requires --reason (T-1317)"
    AckReasonBoilerplate = "frob ack --reason reads as a rubber stamp (T-1317)"
```

## Cache

The SQLite-backed snapshot cache at `.frob/cache.db` (`frob/graph/cache.py`).
Everything stored here is derived and rebuildable from the tracked source
tree -- safe to delete at any time (see Design decisions below).

<!-- frob:describes src/frob/graph/cache.py::connect -->
<!-- frob:describes src/frob/graph/cache.py::set_root -->
<!-- frob:describes src/frob/graph/cache.py::get_root -->
<!-- frob:describes src/frob/graph/cache.py::get_file_meta -->
<!-- frob:describes src/frob/graph/cache.py::touch_file_stat -->
<!-- frob:describes src/frob/graph/cache.py::store_file_data -->
<!-- frob:describes src/frob/graph/cache.py::load_file_data -->
<!-- frob:describes src/frob/graph/cache.py::load_all -->

```python
def connect(path: Path) -> sqlite3.Connection
    # Opens (creating parent dirs) the cache db; wipes and rebuilds on
    # schema mismatch or on a file that isn't a readable sqlite db at all
    # (T-0019/T-0029) -- the cache is derived state, so delete-and-recreate
    # is the honest recovery. Also carries a VERSION FINGERPRINT (T-0243):
    # a `meta.fingerprint` row of frob's version plus every tree-sitter
    # grammar/runtime package version. On a mismatch (a frob or grammar
    # upgrade), the derived rows are invalidated and rebuilt -- the same
    # source bytes can parse to a different symbol/edge set across parser
    # versions, which the schema-version check alone cannot catch.
def set_root(conn: sqlite3.Connection, root: str) -> None
    # Records the snapshot's repo root for a later load_graph.
def get_root(conn: sqlite3.Connection) -> str | None
    # The stored repo root, or None if nothing was ever saved.
def get_file_meta(conn, file_path: str) -> tuple[str, int, int] | None
    # (content_hash, mtime_ns, size) for one file (T-0245) -- the stat pair
    # build_graph/load_graph check first, before reading any file bytes.
def touch_file_stat(conn, file_path: str, *, mtime_ns: int, size: int) -> None
    # Refreshes only the stored stat for a file whose content hash did not
    # actually change (T-0245) -- cheaper than a full store_file_data call.
def store_file_data(conn, *, file_path, content_hash, mtime_ns=0, size=0,
                    symbols, edges, malformed) -> None
    # Replaces every row derived from one file (delete-then-insert, one
    # commit) -- the write side of per-file incrementality.
def load_file_data(conn: sqlite3.Connection, file_path: str) -> tuple[...]
    # Reads back everything previously stored for one file -- a cache hit.
def load_all(conn: sqlite3.Connection, *, stats=None) -> GraphSnapshot
    # Reassembles the full GraphSnapshot from every row currently in the db.
```

### Persistent parse-artifact cache (T-1464)

<!-- frob:describes src/frob/graph/cache.py::store_parsed_artifact -->
<!-- frob:describes src/frob/graph/cache.py::load_parsed_artifact -->

```python
def store_parsed_artifact(conn, *, content_hash: str, fingerprint: str, payload: str) -> None
    # Persists one frob.lang.ParsedFile's own model_dump_json() payload,
    # keyed by (content_hash, fingerprint).
def load_parsed_artifact(conn, *, content_hash: str, fingerprint: str) -> str | None
    # The stored payload for that key, or None on a miss.
```

A `parsed_artifacts` table (schema 4) shares this same `connect`/schema/
fingerprint machinery, but is written under its OWN db file
(`.frob/parse-artifacts.db`, `frob.gates._PARSE_ARTIFACT_CACHE_REL`) rather
than `.frob/cache.db` -- see that constant's comment for why (N
`ProcessPoolExecutor` gate workers racing this table's own schema-ensure
work at once measurably perturbed `.frob/cache.db`'s own concurrent-write
timing enough to newly expose a latent contention incident there,
unrelated to this table's own rows).

Rows are keyed by `(content_hash, fingerprint)`, never by path -- the same
file content parses to the same `ParsedFile` regardless of which of
several identically-content-hashed paths asks for it, and `fingerprint`
(`_compute_fingerprint()`, T-0243's existing version string) folds the
parser/grammar/frob version into the key itself so a version upgrade can
never serve a stale row even before `_check_fingerprint`'s wholesale sweep
runs. `frob.lang._parse_file_with_artifact_cache` is the consumer: it
computes `content_hash` before parsing, checks this table first, and on a
miss stores the fresh `ParsedFile` after `_parse_file_uncached` finishes --
transparent when `frob.lang.PARSE_ARTIFACT_CACHE_ENV` is unset (the
default, single-process case), opt-in only inside a `ProcessPoolExecutor`
gate worker (`frob.gates._stamp_worker_parse_artifact_cache_env` stamps
the env var once, in the pool owner, before any worker starts, and
pre-creates/migrates the db file there too -- workers only ever open an
already-valid file). This is what lets `perf`/`clones`/`dead_symbols`/
`arch`/`sys` (each an independent `ProcessPoolExecutor` job that used to
re-parse + re-extract the whole repo from scratch, T-1217's root-cause
finding) share already-derived artifacts across worker processes and
across `frob check` invocations, instead of paying the tree-sitter parse +
`extract()` walk cost once per gate family.

A locked db past `_with_lock_retry`'s own retry budget degrades to "did
not read/write the cache this time" (a plain parse, or a skipped store) --
never escapes and crashes the whole `frob check` run, since this cache
exists purely to make things faster, never to add a new failure mode a
plain uncached parse never had.

### Lock contention (T-1423)

Concurrent `frob` processes sharing the same `.frob/cache.db` can hit
`sqlite3.OperationalError("database is locked")` on any write (or, more
rarely, a read racing a schema rebuild). `connect`'s connect-time wait and
its schema-application retry (T-0029/T-1239/T-1416) already covered two of
the three places this can happen; `store_file_data`, `set_root`,
`touch_file_stat`, and `connect_readonly` are the third -- an ordinary
read/write path outside schema application. All four now retry through a
contended lock via the shared `_with_lock_retry` helper (same
poll/backoff shape and `_LOCK_TOTAL_TIMEOUT_SECONDS` budget as the
schema-application retry) instead of letting the raw exception escape.

If the budget is exhausted, `cache.CacheLocked` (a narrow
`sqlite3.OperationalError` subclass) is raised instead of the bare sqlite
exception, so a caller can catch exactly this recoverable-contention case.
`build_graph` and `load_graph` do so and report `Err(GraphError.CacheLocked)`
-- a `frob check` run under heavy contention now completes and reports,
rather than crashing with an unhandled exception.

### Mount-filesystem performance (T-0245)

On a latency-heavy mount (WSL's `/mnt/c` via 9p, network shares), each
syscall round-trip costs far more than on a native filesystem -- a pilot
run measured ~0.5ms per `stat` under concurrent load. `build_graph` and
`load_graph` used to read every tracked file's full bytes on every single
invocation just to detect "nothing changed"; that is an open+read+close
per file, every gate run. Both now check a stored `(mtime_ns, size)` pair
first (`get_file_meta` / the `files` table's `mtime_ns`/`size` columns,
schema 3, `_SCHEMA_VERSION` in `src/frob/graph/cache.py`) -- a single `os.stat` per file -- and only fall back to a full
content-hash read when that stat pair has actually moved. A `touch` with
no real edit still avoids a reparse (`touch_file_stat` refreshes just the
stat so the fast path applies again next time). `build_graph` also walks
the tree once (`_walk_repo_files`) instead of a separate source-file
`os.walk` plus a `docs/**` `rglob` that re-walked the same subtree.
`frob.graph.cache._open`'s lock wait now polls in short (2s) increments
instead of one blind 30s `sqlite3.connect(timeout=...)` call, logging a
`cache: waiting on lock at ...` warning the first time a poll actually
blocks, so a concurrent-writer stall is visible instead of looking like a
hang.

## Design decisions

- **Lock covers edge endpoints only, not every symbol.** Locking everything
  would churn `frob.lock` on every commit and drown review signal. Coverage
  of unlinked symbols is enforced separately by the coverage gate.
- **Three digests, facet-selectable acks.** A body-only refactor must not
  invalidate contract docs; a signature change must. Alternative (single
  digest) rejected: it makes every ack a rubber stamp.
- **Renames re-link on failure.** Dangling edge -> gate failure listing
  body-digest-matched candidates. Stable IDs in comments rejected as noise.
- **Cache is SQLite in `.frob/cache.db`, always derived.** Fast incremental
  lookups; safe to delete at any time. Tracked-text source of truth.
- **DSL is line-oriented, no expressions.** Grep-able, trivially parseable
  in any language's comments; a real embedded language rejected for alpha.
- **tree-sitter via `tree-sitter-language-pack`.** One dependency for all
  five grammars; hand-rolled parsers rejected (that lesson is the existing
  Python-only `frob.ast`).

## Generated-file marker

- **`frob.graph._generated.is_generated_source(root, path)`** (T-0234)
  answers "does this file carry a recognized generated-file marker" by
  scanning its first ~20 lines for `GENERATED_MARKER_RE` (`@generated`,
  `do not edit`, `generated by` -- case-insensitive; covers this repo's own
  `frob exports`/`frob deploy generate` headers and the common external
  conventions such as Go/protobuf's `Code generated by ... DO NOT EDIT.`).
- **Deliberately distinct from `[graph] exclude`.** Excluding a path
  (`frob.excludes`) removes it from the graph entirely -- xref, dup, and
  arch lose visibility. A generated-marker file stays fully IN the graph
  (symbols resolvable, xref intact); only the hand-authored-documentation
  obligation (`COV001`, `frob.gates._cov001`) is exempted, since nobody
  hand-documents machine-generated code. Filed from sibling-repo pilot P1's
  gap 23 (a `*.generated.ts` file drawing COV001 demands it had no way to
  satisfy).

## Implementation notes (Phase 2)

- **Source-extension table duplicated from `frob.lang`.** `frob.lang` exposes
  only `supported_languages()` (a label set), not its extension-dispatch
  table, so `frob.graph` walks the tree with its own small, documented copy
  (`.py .ts .tsx .rs .c .h .cpp .hpp .cc .hh`). Adding an extension-listing
  API to `frob.lang` for this one caller was judged out of scope.
- **`ParsedFile.path` is corrected to repo-root-relative.** `frob.lang`
  renders `ParsedFile.path` cwd-relative (or absolute if outside cwd) --
  `frob.graph` always calls with an absolute path and rewrites `.path` to the
  root-relative form before computing symrefs or directive edges, so a
  symref never depends on the caller's working directory.
- **A per-file parse failure does not fail the whole build.** `build_graph`
  logs and skips a file that fails `parse_file` (unsupported extension,
  unreadable, unparseable); the `BuildError = GraphError | LangError` return
  type exists for future callers that need to surface a hard failure (e.g. a
  missing `root`), not for routine per-file skips.
- **Cache deletions are pruned.** Any file present in the cache but no
  longer seen during a `build_graph` walk (deleted or renamed) has its rows
  removed, so `GraphSnapshot` never carries stale symbols/edges for a file
  that no longer exists.

## Dependencies

- `frob.lang` -- ParsedFile (symbols + comments) per source file.
- `tree-sitter`, `tree-sitter-language-pack` -- grammars (new deps).
- `pydantic`, `typani` -- models and Results.
- stdlib `sqlite3`, `hashlib`.

## Integration points

- `frob.gates` consumes `GraphSnapshot`, `DriftReport`, and joins edge
  targets against tickets/docs/invariants.
- CLI: `frob graph build|query|why`, `frob ack <ref...> [--facet]` runners
  under `frob/app/`.
- `frob check` triggers `build_graph` (incremental) at the start of a run.
