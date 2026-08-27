# frob.graph -- obligation graph engine

One sentence: a persistent registry of every symbol's identity and digests,
plus typed edges declared in comments, so that any change to code, docs, or
contracts is detectable statically -- a type checker for obligations.

Built on `frob.lang` (tree-sitter): uniform symbol and comment extraction
for Python, TypeScript, Rust, C, and C++.

## frob graph

Four subcommands, all read-only against the persisted cache: `frob graph
build` (re)builds the graph cache from scratch, needed after a change
`frob check`'s own incremental rebuild path did not pick up; `frob graph
query REF` resolves a `path::Qualified.Name` symbol ref (see "Symbol
references" below for the exact form) and prints its stored edges;
`frob graph why REF` explains a ref's current drift/ack status and what
remedies it (e.g. an `frob ack` call, a doc edit); `frob graph affects
REF` reports the transitive closure of every uses-contract dependent plus
every doc/test edge a change to `REF` would affect -- the same
"blast radius" query `frob ack`/`frob check`'s DRIFT family reason about
internally.

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
def parse_file(path: Path, *, expect_heterogeneous: bool = False) -> Result[ParsedFile, LangError]
    # WHY: single entry point; language dispatch is internal (by extension).
    # `expect_heterogeneous=True` (T-2575) declares that unsupported
    # extensions are routine at this call site -- see docs/modules/lang.md.
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

## Evidence reach (T-3046)

<!-- frob:describes src/frob/graph/reach.py::EvidenceReach -->
<!-- frob:describes src/frob/graph/reach.py::ReachResult -->
<!-- frob:describes src/frob/graph/reach.py::classify_evidence_reach -->

"Does this bound pytest evidence actually EXERCISE the code it certifies"
-- the check `frob.ci_validity` (T-2985) answers for a CI run's staleness,
applied here to the ticket-evidence question the M6 design-audit finding
named: T-3005 and T-3007 both landed with evidence bound to
`tests/unit/strata/test_parse.py` node ids -- parser tests that never
touch the Rust graph code either ticket added. Both passed
`frob.gates.evidence_covers_scope` (D-02) because that check has a
self-declaration route with no verification: an evidence id whose OWN
file is directly named in `ticket.evidence_scope` (T-1944, a bare pointer
with no write-lease claim) counts as covering, regardless of whether
anything in that file's tests exercises the ticket's real work.

```python
# frob/graph/reach.py
class EvidenceReach:
    REACHES = "reaches"
    DOES_NOT_REACH = "does_not_reach"
    UNKNOWN = "unknown"

class ReachResult(BaseModel):
    evidence: str
    status: str   # one of EvidenceReach's three values
    reason: str

def classify_evidence_reach(root: Path, snapshot: GraphSnapshot,
                             scope: Sequence[str], evidence: str, *,
                             evidence_scope: Sequence[str] = ()) -> ReachResult
```

- **Three-way rule**: `REACHES` when the test's own call TOKENS
  (`RawSymbol.body_tokens`, public or private -- the direct-call case,
  the dominant real pattern) name a scoped symbol's short name, OR the
  test's private-callee `frob.graph.callgraph.build_call_graph`/`closure`
  reaches one transitively, OR the test's own file is directly in
  `scope` (a real write-lease claim, the one case D-02's existing
  co-located-test trust is sound). `DOES_NOT_REACH` when none of those
  hold and reachability WAS computable. `UNKNOWN` when it could not be
  computed at all: the test symbol does not resolve in the graph, or
  `scope` names a non-Python source file (`.rs`/`.c`/`.cc`/`.cpp`/`.h`/
  `.hpp`/`.ts`/`.tsx`/`.go`/`.java`/`.rb`) the call graph cannot represent
  -- exactly T-3005/T-3007's shape.
- **`scope` vs `evidence_scope` are NOT interchangeable here**: only
  `scope` (a real lease) grants the co-located-file shortcut.
  `evidence_scope` files still widen the file set resolved/parsed (a
  test needs its own file to resolve `test_ref` and compute its call
  tokens/closure at all) but never count as a scope MEMBER to reach
  into -- an evidence-id whose file is named ONLY in `evidence_scope`
  must prove reach like anything else, with its own file's symbols
  excluded from "reached" so it cannot pass by calling its own
  neighbors. This is the exact hole M6 found; a test proving the
  fix intentionally reproduces it (`test_evidence_scope_alone_does_not_
  launder_reach`).
- **Rust/native-only decision**: a scope with no representable Python
  file is `UNKNOWN`, always, no matter which pytest id is cited. "There
  is no Python test that reaches this" (T-3007's own Done report: the
  crate's own `cargo test` is the real evidence) is a legitimate answer,
  but it must be an explicit, recorded `UNKNOWN` -- never silently
  accepted as a pass because an unrelated pytest id happened to be
  green.
- **Measured (2026-08-26, this repo's own ledger, `scripts/
  measure_evidence_reach.py`)**: of 495 non-cmd evidence ids bound across
  every DONE ticket with a declared scope, 467 (94.3%) REACHES, 7 (1.4%)
  DOES_NOT_REACH, 21 (4.2%) UNKNOWN (native-only scopes, T-3005/T-3007
  among them). Reported honestly rather than tuned quiet -- see
  `scripts/measure_evidence_reach.py`'s own docstring for why this ships
  as a standalone measurement tool rather than a wired `frob check` gate
  stage yet (the job-table file, `src/frob/gates/__init__.py`, and
  `docs/modules/gates.md` were both leased by T-3009 while T-3046 was
  worked); wiring `evidence_reach_gate` at WARN severity into the live
  pipeline is a follow-up ticket, filed blocked on T-3009 landing.
- **Not wired into `evidence_covers_scope`/D-02 itself yet, deliberately**:
  today D-02 still accepts the `evidence_scope` self-declaration route
  unchanged (closing it outright would need a decision about EVERY
  existing binding that route quietly accepts, not just the two this
  audit named) -- this module is the classifier and the measurement,
  landed first so the repo-wide count is known before any gate is
  tightened. See the follow-up ticket for wiring it in as an enforcement
  point.

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

### Attribution-safe reference graph (T-2156)

<!-- frob:describes src/frob/graph/callgraph.py::build_reference_graph_module_scoped -->

`build_reference_graph(root, paths)`'s short-name resolution is
DELIBERATELY over-inclusive: it matches a called name against the
codebase-wide short-name index and wires an edge to EVERY private
candidate sharing that name, in ANY file, discarding the candidate's own
path. That is correct and safe for its original consumer (T-0422's
dead-symbol gate, "is this symbol referenced anywhere at all" -- an extra
edge there only means fewer false dead-code positives).

`frob.verify._attribution` (T-1690) reuses the same graph shape for a
different question -- CAUSAL reachability, "did commit X's touched
symbols reach finding F" -- where a spurious edge manufactures a false
positive attribution. Observed directly (T-2156): a private helper named
`_run` is independently defined, with the identical name, in 17 different
test files (`_commit_all` in 18) -- an ordinary git-fixture-test naming
convention, not an accident -- so the blanket short-name match wired a
fabricated edge from one test's `_run` caller to an unrelated file's
`_run`, attributing a finding to the wrong land. The same over-matching
also explains the `commit=None` findings that plagued attribution before
this fix: `_attribution.py`'s "zero or MORE THAN ONE candidate reaching =
unattributed" rule fired correctly once collisions inflated the
reaching-candidate count past one -- the rule was right, the graph feeding
it was wrong for this consumer.

`build_reference_graph_module_scoped(root, paths)` is the fix: same
shared `_parse_package`/`_short_name_index`/`_referenced_names`
extraction and indexing as `build_reference_graph` (no duplicated parsing
logic), but a cross-file candidate only resolves when the caller's file
actually IMPORTS the candidate's file (`frob.lang.extract_imports` +
`frob.lang.resolve_local_import`, best-effort -- a file whose imports
cannot be extracted just contributes no cross-file edges). A same-named
collision between two files with no import relationship now resolves to
NO edge instead of a fabricated one.

`build_reference_graph` itself is UNCHANGED BY DEFAULT and still used
directly by T-0422's dead-symbol gate, which needs its broader recall --
narrowing the shared graph globally would risk resurrecting dead-symbol
false positives repo-wide to fix an attribution-only problem. Two
consumers with genuinely different correctness requirements getting two
resolutions here is deliberate, not the T-1966 "one rule, two homes"
defect -- the difference is documented, in one shared module, not
independently reinvented. See `tests/unit/test_callgraph_module_scoped.py`
for the reproduction of the fixed shape.

**T-2188 update, and the BLOCKER it filed (T-2195, now FIXED).** T-2156's
own mechanism (import-verified cross-file resolution, `_local_imports_
by_path`) is now shared, opt-in, by `build_call_graph`, `build_reference_
graph`, and `build_ordered_call_graph` too, via a `verify_imports: bool =
False` parameter on each -- the same "resolve a cross-file candidate only
when the caller's file imports it" check `build_reference_graph_module_
scoped` pioneered, generalized rather than reimplemented a second time
(the T-2156 incident -- `_run`/`_commit_all` collisions -- is not unique
to attribution; COV006, DEAD001, and PROTO001-005 read the SAME shared
`by_name` index and were equally exposed). Defaults to `False` on every
function -- flipping any of COV006/DEAD001/PROTO001-005 to `verify_
imports=True` is still a separate ticket's job (T-2188 itself, and it
was explicitly NOT this ticket's job either), but the BLOCKER that made
doing so unsafe is now cleared: T-2195 found `frob.lang._nodes.resolve_
local_import`'s python branch resolving `None` for every absolute
src-layout specifier (`frob.tickets._land`, resolved only against bare
`root`, never `root/src`) AND every relative specifier (`._land`,
`..lang._nodes` -- the leading-dot branch did not exist at all) --
measured blast radius on this repo's own tree: DEAD001 46 -> 241, COV006
30 -> 622 findings when trialed with `verify_imports=True`, and the
independently-reproduced discovery that this ALSO made `frob cycle`
report "no cycles found" on a byte-identical import cycle that a
top-level (non-`src/`) layout correctly detected. `resolve_local_import`
now resolves absolute specifiers against every `pyproject.toml`-declared
source root (`[tool.setuptools] packages.find.where`, `package-dir`, or
the hatch-wheel-packages equivalent -- never a hardcoded `src/` lexical
special case, so a different declared layout picks up the same way) in
addition to bare `root`, and resolves relative specifiers by walking up
from the importing file's own directory per leading dot, matching
python's own relative-import semantics. Per-consumer controls now exist
for all three previously-vacuous consumers (`tests/test_lang.py::
TestResolveLocalImportConsumers`): `frob.cycle` detects the SAME planted
cycle in both a top-level and a src-layout project; `frob.arch._layering.
_resolve_import_targets` resolves a non-empty target set AND `check_
layering_violations` flags a real disallowed cross-layer import, on a
src-layout fixture, where before the fix `specs=19 resolved=0`-shaped
readings made layering enforcement silently vacuous on frob's own repo.
This additionally means `build_reference_graph_module_scoped`'s own
T-2156 fix has never been verified against a genuine cross-file
attribution on this repo's own tree via THIS docs section's prior
uncertainty -- `tests/test_graph.py::TestBuildCallGraphVerifyImports::
test_cross_file_candidate_resolves_when_caller_imports_it` already
exercises that positive case directly (an absolute same-directory
import, unaffected by the src-layout/relative gap this ticket closed),
so it was never actually blocked on this fix; re-verifying it against a
src-layout positive case specifically remains open work for whichever
ticket flips a real consumer's default. The `scope_private_helper_gaps`
(T-0998/T-1012) consumer passes `verify_
imports=False` explicitly (matching the default, kept for documentation
clarity) -- it has a permanent, different correctness requirement (same-
directory co-location, not import reachability) unrelated to this
blocker.

### Self-disclosure of a silently degraded capability (T-2683)

<!-- frob:describes src/frob/graph/callgraph.py::capability_gap_disclosure -->
<!-- frob:describes src/frob/graph/callgraph.py::CallGraph -->

`build_call_graph`'s output can be silently incomplete for a language
whose `call_graph` (or, when `verify_imports=True`, `import_graph`)
adapter capability is a live registry `KNOWN_GAP` (docs/modules/
lang.md#optional-capability-degradation-t-1599) -- before T-2683, a
consumer had no way to learn this from the `CallGraph` object itself; it
would have to separately query `frob.lang._support.derive_capability_
registry` and cross-reference it against the languages it happened to
scan. `CallGraph.degraded_languages` closes that: `build_call_graph`
computes it on every call (via `capability_gap_disclosure`, the shared
primitive) and logs a WARNING when non-empty, so the OUTPUT announces
its own incompleteness rather than staying silent about it.

```python
def capability_gap_disclosure(languages: frozenset[str], capability: str) -> tuple[str, ...]
```

One human-readable warning per language in `languages` whose
`capability` cell is `KNOWN_GAP` in the live registry -- empty in the
common case (every registered language is `call_graph`/`import_graph`
`IMPLEMENTED` today, T-1599). `frob.cycle.import_graph_gap_disclosure`
(`src/frob/cycle/__init__.py`) is the same primitive pre-bound to
`import_graph`, exposed for `frob.cycle.graph`'s own future use.

<!-- frob:describes src/frob/cycle/graph.py::DependencyGraph.degraded_languages -->
<!-- frob:describes src/frob/cycle/graph.py::find_cycles -->

T-2700 finished the wiring T-2683 deliberately left half-done:
`DependencyGraph.degraded_languages` derives the languages present from the
graph's OWN node ids (every real caller -- `frob.app.cycle_runner`,
`frob.check._python`'s CYCLE001 gate, `frob.arch._smells` -- adds nodes
as project-relative file paths, so the suffix alone is enough, no extra
argument needs threading through any of them) and `find_cycles` logs a
WARNING when it is non-empty, the same self-disclosure posture `build_
call_graph` already has for `CallGraph.degraded_languages`. Because
`find_cycles(graph)` is the one call every consumer already makes, this
reaches all three real callers -- including the CYCLE001 gate `frob
check` runs -- without editing any of those three files: a repo whose
language has a live `import_graph` `KNOWN_GAP` gets cycle output that
NAMES the degradation, and a fully-supported repo gets no added log
noise (`tests/test_graph.py::TestDependencyGraphDegradedLanguages`
proves both directions).

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

## Path-confinement census

<!-- frob:describes src/frob/graph/summary.py::compute_confinement_summaries -->
<!-- frob:describes src/frob/graph/summary.py::scan_confinement_facts -->
<!-- frob:describes src/frob/graph/summary.py::ConfinementState -->
<!-- frob:describes src/frob/graph/summary.py::FsWriteSite -->
<!-- frob:describes src/frob/graph/summary.py::FunctionConfinement -->
<!-- frob:describes src/frob/graph/summary.py::ConfinementCensusResult -->

REPORT-ONLY (user directive, 2026-08-18): a MEASUREMENT, not a gate.
Nothing described here is wired into `frob check`; no severity is
assigned to any finding yet. This is the first deliverable of the
"confined to" provability epic (T-2501) -- a real, committed-to CENSUS
of how many `fs.write` call sites under `tests/**` can be PROVEN confined
to a sanctioned root today, using the existing protocol-summary engine's
own SCC-ordered worklist (T-0745's design constraint: "one engine, not
two") rather than a second call-graph traversal.

### The lattice

`ConfinementState`: `ROOTED` (provably derived from `tmp_path`/
`tmp_path_factory`/`tmpdir`/`tempfile.*` via only confinement-preserving
ops: `/`-join or `os.path.join` with a relative literal, `.with_name`/
`.with_suffix`/`.with_stem`), `ESCAPED` (provably outside one: an
absolute string literal, `Path.home()`, `os.getcwd()`,
`os.path.expanduser`, an `os.environ` lookup), `UNKNOWN` (unprovable with
this pass's own precision, or transitively poisoned by an unresolved
callee -- never rendered as a pass, same NO-FAIL-SILENT posture
`FunctionSummary.poisoned` already holds above).

### Engine shape

- `scan_confinement_facts(root, paths)` -- the ONE function that reads
  files: `ast.parse`s every `.py` file in `paths`, extracting each
  top-level function/method's OWN facts (a single linear forward pass
  over its top-level statements only -- see `_scan_function_facts`'s own
  docstring for the exact, disclosed branch-insensitivity limitation)
  into a private `_RawFuncFacts` record. Not part of `__all__` --
  `_RawFuncFacts` itself is an internal detail; callers only see the
  `dict[str, _RawFuncFacts]` this returns, threaded straight into
  `compute_confinement_summaries`.
- `compute_confinement_summaries(facts, entrypoints)` -- pure, no
  filesystem I/O (matches `compute_protocol_summaries`'s existing
  offline posture): resolves each raw fact's `_Pending`/`_ParamRef`
  markers into a real `ConfinementState` bottom-up over the SAME
  `_universe`/`_reachable`/`_tarjan_sccs` worklist `compute_protocol_
  summaries` above already builds, via its own join (`_resolve_state`/
  `_finalize_function`) instead of `_join_from_callees`'s five-set union.
  Pass `entrypoints=list(facts)` (every scanned function is its own
  entrypoint) to count every site regardless of call-graph reachability
  -- this consumer wants a full census, not a dead-code exclusion.
- `FsWriteSite` -- one recognized `fs.write`-shaped call site
  (`open(path, "w"/...)`, `.write_text`/`.write_bytes`), its final
  `state`, and `poison_source` (the private callee symref responsible
  for an `UNKNOWN` verdict, when attributable to one specific
  unresolved/unprovable helper call rather than this pass's own
  in-function precision limit).
- `FunctionConfinement` -- one function's own sites plus its RETURN
  value's confinement contract: `return_always` (a fixed state
  independent of its own parameters) or `return_depends_on_param` (the
  "`param0` confined => result confined" shape the ticket names,
  single-positional-argument heuristic -- see `_Pending`'s docstring).
- `ConfinementCensusResult` -- `sites` (every recognized site, final
  verdict), `not_analyzed` (same NO-FAIL-SILENT channel as the protocol
  engine), `poison_sources` (`{callee_symref: unknown_site_count}`,
  the "which helpers are the biggest poison sources" breakdown T-2504's
  own ticket body asked for), and a `.counts` property giving the exact
  `{rooted: n, escaped: n, unknown: n}` PROVEN/ESCAPED/UNKNOWN census
  number.

### Disclosed precision limits (read before trusting a specific verdict)

- **No real control-flow join.** `_scan_function_facts` only tracks
  local-variable assignments made as TOP-LEVEL statements in a function
  body; an assignment inside an `if`/`for`/`while`/`with`/`try` block is
  invisible to later top-level code. This is a deliberate,
  precision-over-recall bias: it can only ever under-prove (push a real
  `ROOTED` toward `UNKNOWN`), never fabricate a false `ROOTED`/`ESCAPED`.
- **No interprocedural argument substitution into a callee's OWN body.**
  A private helper `def _write_fixture(tmp: Path): (tmp / "x").write_text
  (...)` (writing directly to its own plain-`Path` parameter, WITHOUT
  returning it) resolves that internal site `UNKNOWN` regardless of what
  every call site actually passes -- only a helper's RETURN value gets
  the param-dependent propagation callers benefit from
  (`return_depends_on_param`). Building real per-call-site argument
  substitution is a second, genuinely larger interprocedural analysis
  this report-only pass deliberately did not build (see the 2026-08-18
  census run below: this is the actual DOMINANT source of `UNKNOWN`,
  not helper-poison propagation).
- **Single-positional-argument heuristic.** `_Pending` only tracks the
  FIRST positional argument's confinement when deferring to a callee's
  `return_depends_on_param` -- a multi-argument helper whose result
  depends on its second/keyword argument is not modeled.

### Census run (2026-08-18, first measurement)

Run against every `.py` file under `tests/**` on this repo (608 files;
`tests/fixtures/lang/broken.py` skipped, a deliberately-malformed parse
fixture -- `scan_confinement_facts` logs the skip and omits it, per its
own docstring, rather than crashing the whole scan):

```
functions scanned: 11545
total fs.write sites recognized: 2989
counts: {rooted: 2248, escaped: 1, unknown: 740}
poison_sources: 5 distinct callees, 13 UNKNOWN sites attributed to one
  (transitive helper-call poisoning, T-0809-style propagation)
UNKNOWN with NO attributable poison_source: 727 sites (98% of all UNKNOWN)
```

The user's original ~352 figure (from a strata via-list enumeration)
counted DECLARED FILES, not call sites -- corrected by the user
mid-drive; 2989 is the real call-site count this pass recognizes.

**The finding, not a failure:** the ticket's own anticipated risk --
"ONE unresolved callee inside a widely-used test helper can poison
hundreds of sites" -- does NOT materialize here. Helper-call poison
propagation accounts for only 13 of 740 `UNKNOWN` sites (five distinct
helpers, none with more than 3 attributed sites: `tests/integration/
test_exports_write.py::_make_pkg` (3), plus four with 1 each). The
DOMINANT source (727 sites, 98%) is this pass's own documented
interprocedural-argument-substitution gap above: dozens of small,
file-local `_init_repo(path)`/`_make_pkg(pkg, name)`/`git_init(root)`-
shaped helpers that write DIRECTLY to their own plain-named `Path`
parameter (never literally named `tmp_path`, never returned) -- e.g.
`tests/test_ticket_land.py` alone accounts for 208 of the 727. Only one
`ESCAPED` site was found in the entire `tests/**` tree (`tests/test_
check_runner.py:359`), consistent with the ticket's own prediction that
`ESCAPED` should be rare and each instance worth a look, not a systemic
pattern.

**What would have to become provable first, if this is to become a
gate:** the argument-substitution gap above, not helper-poison
propagation. A follow-up pass that lets a helper's OWN internal write
site inherit `ROOTED` when EVERY call site in `facts` passes a `ROOTED`
argument to the corresponding parameter (a much smaller extension than
full interprocedural substitution: no per-call-site cloning, just a
whole-program "is this parameter ALWAYS called with a confined
argument" check per helper, still bottom-up on the same SCC worklist)
would likely resolve the large majority of the 727 -- concentrated in a
small number of files (`tests/test_ticket_land.py` alone is 28% of it).
This is NOT built by this ticket; T-2504's own scope is the census only.

### Parameter-position confinement credit (T-2519)

<!-- frob:describes src/frob/graph/summary.py::_compute_param0_credit -->

REPORT-ONLY still (nothing wired into `frob check`; no severity
assigned): a targeted precision improvement over T-2504's first pass,
closing part of the "727 of 740 UNKNOWN is one disclosed precision
limit" gap that census identified.

A private helper's OWN `fs.write` site that references its first
positional parameter DIRECTLY (`_write_fixture(tmp: Path): (tmp /
"x").write_text(...)`, never returning `tmp`) now resolves `ROOTED`
instead of an unconditional `UNKNOWN`, but ONLY when `_compute_param0_
credit` can prove EVERY observed call to that helper anywhere in the
scanned corpus passes a concrete `ROOTED` argument for that parameter --
a single unrooted/unprovable caller anywhere disqualifies credit for
ALL of that helper's sites (never a partial, unsound pass). A helper
that reassigns its own parameter to something escaping (`tmp =
Path("/etc/x")`) is unaffected -- that reassignment already resolves
`ESCAPED` through the existing local-variable tracking before this
credit mechanism is ever consulted, so an escaping helper can never
receive credit by construction, not by a special-cased check.

Same single-first-positional-argument scope `_Pending`'s own `arg_state`
already uses (disclosed there) -- a helper credited/blamed via any OTHER
parameter position, or via a keyword-only argument, is not modeled.

**Census re-run (2026-08-18, same `tests/**` corpus, apples-to-apples
against the SAME file set to isolate the credit mechanism's own effect
from unrelated corpus growth between census runs):**

```
                    BEFORE T-2519   AFTER T-2519    DELTA
ROOTED                   2255           2323         +68
ESCAPED                     1              1           0
UNKNOWN                   741            673         -68
```

**The finding, not the hoped-for number:** the ticket's own framing
("give parameter-position credit to close 727 of 740 UNKNOWN sites")
anticipated resolving the large majority of the gap; the credit
mechanism as built and measured resolves only 68 of 727 (9.2%). Two
concrete, disclosed reasons, in order of actual measured impact:

1. **The private-callee-only resolution boundary, not the credit rule
   itself, is the dominant remaining limiter.** Both this engine and the
   underlying `CallGraph` it is hosted on (`build_call_graph`) only ever
   resolve calls to PRIVATE (leading-underscore) callees -- a deliberate,
   pre-existing design choice (see "Call graph" above: this is what lets
   `closure` stop at the public API boundary for free). Inspecting
   `tests/test_ticket_land.py` (208 of the original 727, the single
   largest concentration) shows most of its remaining UNKNOWN sites are
   NOT `_write_fixture(tmp)`-shaped helper calls at all -- they are
   writes to a local variable (`wt`, `repo`) assigned INSIDE a test
   METHOD from a call to a PUBLICLY-named test fixture/helper (no
   leading underscore), which this pass's `_classify_call` never even
   attempts to track as a `_Pending` marker, by the same convention
   `build_call_graph` already applies repo-wide. Extending param0-credit
   (or ANY interprocedural credit) to public-named helpers would require
   a genuinely different call-resolution boundary, a repo-wide policy
   decision out of this ticket's own scope.
2. **The all-callers-rooted + single-first-positional-argument
   constraints** (both deliberate, both load-bearing for soundness) cut
   real cases too: any helper called from even one test with a
   not-provably-rooted argument (common in fixture-heavy test files that
   mix `tmp_path`-derived and hand-built paths across different tests)
   gets no credit at all, and a helper crediting a SECOND or keyword
   parameter is invisible to this pass regardless of how it is called.

**What this means for the epic's gate decision:** parameter-position
credit is a real, sound, positive-control-verified improvement (verified
both directions: the escaping-param negative control, T-2519's own
ticket-mandated third control, correctly stays `ESCAPED`/gets no
credit), but it is NOT, on its own, sufficient to convert the bulk of
the remaining UNKNOWN tail into `ROOTED`. The single largest further
lever is the private-callee-only resolution boundary identified above --
a repo-wide call-resolution policy question, not a lattice change,
appropriately out of scope for a report-only measurement ticket.

## Comment DSL

<!-- frob:describes src/frob/graph/dsl.py::parse_directives -->
<!-- frob:describes src/frob/graph/dsl.py::markdown_anchors -->

- `parse_directives` -- extracts every `frob:` directive comment in a
  parsed file into typed `Edge`s (or `MalformedDirective`s when a line
  fails to parse).
- `markdown_anchors` -- extracts `describes`-verb HTML-comment anchors
  (`frob:describes <symref> [facet]`) from a markdown doc, binding each to
  the nearest preceding heading slug. Also returns (T-1968) a
  `MalformedDirective` for any other `<!-- frob:<verb> ... -->`
  HTML-comment directive it does not itself turn into a real edge -- see
  "Unhandled markdown directives" below.

### Unhandled markdown directives (T-1968)

<!-- frob:describes src/frob/graph/dsl.py::_unhandled_markdown_directive -->

Before T-1968, `markdown_anchors` never checked whether an
`<!-- frob:<verb> ... -->` HTML-comment directive it did not itself
recognize (only `describes`/`enumerates`/`until`) was actually read by
ANYTHING else -- a real, deliberate waiver like
`<!-- frob:waive DOC006 reason="..." -->` was accepted as silent prose,
no error, no warning, no suppressed finding, and no way for the author
to learn it did nothing.

Several gates independently invented their own tiny per-rule regex
reading `frob:waive <RULE> reason="..."` directly out of markdown text,
entirely outside this module: `frob.gates._refs._md_waived_rules`
(REF001/REF002), `frob.gates._docptr._WAIVE_DOC006_RE` (DOC006),
`frob.gates._docblocks_refs._WAIVE_DOC004_RE` (DOC004),
`frob.gates._inv._DOC_WAIVE_MARKER_RE` (INV003/INV004),
`frob.gates._bug_repro._BUG002_WAIVER_RE` (BUG002, over a
ticket's own body text -- NOT this module, so a malformed `reason=`
there is not caught by anything described on this page; see T-2857's
follow-up ticket). `_unhandled_markdown_directive` treats exactly
that set (`_MD_WAIVE_HONORED_RULES`) as handled; a `frob:waive` naming
any OTHER rule id, or any verb outside `_MD_HANDLED_VERBS` (`frob.gates.
_docblocks`'s `frob:generated-start`/`frob:generated-end` table-fence
markers, T-1011, plus a handful of other-subsystem markers) becomes a
`MalformedDirective` -- markdown's half of DSL001's own catch-all
contract ("no frob: comment that fails to parse into a real edge goes
unreported").

`describes`/`enumerates`/`until`/`ticket`/`doc` are NOT in
`_MD_HANDLED_VERBS` (T-2857): `_unhandled_markdown_directive` only ever
runs on a line after `markdown_anchors`'s own strict per-verb regex has
already tried and failed to turn it into a real edge, so a shape-matched
`frob:describes`/etc reaching this check is proof the line is broken
(a bad symref -- e.g. an embedded space left by a line-wrap gone wrong,
or a `frob:enumerates` missing its mandatory `members="..."` attribute),
never a false positive on something that still parses.

`_MD_WAIVE_HONORED_RULES` membership alone used to be sufficient to
accept a `frob:waive` line as clean (T-2857 mode 1): the check for the
opening `reason="` never verified the value actually CLOSED before
`-->`, so a bare unescaped `"` inside the reason text silently produced
zero diagnostic while also suppressing nothing (each per-rule gate's own
regex above has the exact same closure gap independently). The value is
now matched with a backslash-escape-aware grammar (`\"` does not
terminate it, matching this repo's own existing informal convention for
a literal quote inside a reason) so a genuinely early close -- leftover
text before `-->` -- is reported; a value that has no closing quote on
this physical line at all is left alone, since a legitimate `frob:waive`
reason can span multiple physical lines and this scanner is line-by-line
by design.

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

### The `frob:quote(...)` mention escape (T-1970)

<!-- frob:describes src/frob/graph/dsl.py::mask_frob_mentions -->

The DSL had no mention/use distinction: prose ABOUT a directive was
parsed AS one. Measured twice in one session: a discharge comment
quoting `follow_up="T-1956"` verbatim while explaining the follow-up had
already been handled was read as a still-live citation
(`TicketError.LiveTrackerCited`); the reworded replacement, describing a
removed `frob:waive WIRE001` directive, was then read as a malformed
directive of its own (DSL001). Both refused real lands over pure
English wording, with no way to write correct documentation of the DSL
without triggering it.

`frob:quote(...)` is the one explicit escape: any text a `frob:quote(`
... `)` span wraps is a MENTION, not a directive. `mask_frob_mentions`
replaces the WHOLE span (wrapper delimiters and contents) with
same-length `.` filler before any directive-shaped matching runs,
preserving every other character's column position. Single-level (no
nested parens) -- directive attribute values in this DSL are always
`key="value"` quoted strings, which never themselves need parens.

Recognized by every scanner that reads directive-shaped text, not just
the parser that motivated it:

- `frob.graph.dsl.parse_directives` (code comments) and
  `markdown_anchors` (markdown) both mask before matching, at the
  single earliest point each function ever inspects text.
- `frob.tickets._live_tracker.live_tracker_citations` (a separate `git
  grep`-based citation scan, unrelated to this module's own parser) --
  `_drop_escaped_mentions` re-runs each hit's matched pattern against
  the masked text and drops the hit if the match existed only inside
  the escape (docs/modules/tickets-landing.md#live-tracker-citation-preflight-t-0854).

An UNESCAPED real directive elsewhere on the same physical line is
unaffected -- masking only touches the wrapped span, never the whole
line, so escaping one mention never silently un-honors a genuine
directive next to it.

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
