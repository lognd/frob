# frob.perf -- profiling, heat-maps, and algorithmic-smell detection

One sentence: frob gains a performance layer with three interlocking
pieces -- run-under-profiler (`frob perf profile`), symbol-level heat-maps
projected onto the obligation graph (`frob perf heat`), and static PERF
rules that flag linear scans a better data structure would eliminate --
so "hot AND quadratic" becomes a ranked, gated finding instead of a
debugging session. (Origin: the malmberg incident -- a linear search
across 28k files whose fix was literally a hashset.)

## The three pieces

1. **Profile**: `frob perf profile -- <argv>` runs the command under
   cProfile (python) and stores a content-addressed artifact in
   `.frob/perf/<sha>.pstats`; `frob perf profile --tests` wraps the
   `[[test.runner]]` python entry so the suite itself is the workload.
   Non-python runners are recorded design (py-spy/perf/samply adapters,
   0.3.x); the artifact model is runner-agnostic from day one.
2. **Heat-map**: `frob perf heat [--json]` joins pstats data onto the
   graph snapshot -- pstats rows carry (file, line, function), symbol
   spans locate the enclosing SymbolRecord -- and renders symbols ranked
   by cumulative time with per-symbol self/cumulative/ncalls columns and
   a bar rendered in ASCII blocks. `--annotate <file>` prints the file
   with per-line hit/time gutters (the classic heat listing).
3. **PERF rules** (static, tree-sitter over frob.lang, shares the
   frob.policy pattern-query engine):

| Rule | Fires when | Suggested fix |
|---|---|---|
| PERF001 | membership test (`x in lst`, `.includes(...)`, `Vec::contains`) where the needle-holder is a list/array/Vec AND the test executes inside a loop (or a function called per-item of a loop in the same file) | build a set/HashSet/Map once, test against it |
| PERF002 | `.index()`, `.indexOf()`, `.find(==)`, `list.count()` inside a loop | dict/Map from key to index/count, built once |
| PERF003 | nested loops over two collections with an equality comparison between their items (the O(n*m) join) | index the inner collection by the compared key |
| PERF004 | `sorted()`/`.sort()` inside a loop over data unchanged by the loop | hoist the sort, or use a sorted container |
| PERF005 | recursive function (self- or same-file mutual recursion) with no provable termination measure | add `frob:invariant terminates reason="..." measure="..."`, or restructure so termination is provable |
| PERF006 | tail-recursive function with no proven depth bound (Python has no TCO -- unbounded input depth is a stack-overflow/DoS bug) | rewrite as an explicit loop, or prove a static depth bound |
| PERF007 | a `frob.toml`-configured expensive call (`[[perf.heavy]]`) invoked from 2+ distinct top-level symbols with no shared-cache decorator on its own definition (T-0413, the PERF META-GAP) | wrap the call target in `memoize_per_run`/`lru_cache`/`cache`, or route every call site through one shared call |
| PERF008 | a loop body's call site is directly, or transitively (via a local call-graph BFS), a process-spawn/directory-walk effect, and every argument at the call site is loop-invariant (T-0775) | hoist the call out of the loop, memoize its result, or add a reasoned `frob:waive PERF008 reason="..."` (e.g. freshness under concurrency) |
| PERF009 | a hot-graph section's current-run sketch (`frob perf collect`) shifts beyond `[perf.sketch].ratchet_tolerance` (default 50% relative) at p50 or p90 versus its stored prior (T-0712) | investigate the regression named in the finding (both decile sets are printed); the ratchet is WARN-tier, waivable per the persisted finding's `.frob/perf/ratchet_findings.json` entry |
| PERF012 | a function's body calls two or more DISTINCT locally-known callees that each (directly, or transitively via a local call-graph BFS) spawn a subprocess with the textually-identical (whitespace-normalized) argument shape -- a duplicated, not-shared expensive spawn on one call path (T-0919, the `frob ticket done-report` two-full-check-spawns incident) | share one spawn's result between the callees instead of paying for it twice, or add a reasoned `frob:waive PERF012 reason="..."` (e.g. a genuinely deliberate independent re-run) |

Severity: PERF001-004 are `warn` by default (static size-blindness is real
-- a 3-element list is fine as a list); promotable per-repo via
`[gates.severity]` (`PERF001 = "error"`). PERF005/PERF006 are `error` by
default -- unlike the lexical smells, unreasoned unbounded recursion is a
control-flow hazard (T-0290), not a size-blind heuristic. PERF007 is
`error` by default and opt-in via config (see below) -- an unconfigured
project gets zero PERF007 checking, never a false positive from a guess
at what "expensive" means for it. PERF008/PERF009/PERF012 are `warn` by
default (undecidable loop-invariance, a regression ratchet, and
undecidable cross-callee duplication all lean toward firing over missing
a real issue -- recall over precision, same posture as PERF007's own
opt-in-only calibration but without an opt-in gate, since all three
structurally cannot false-positive on a project with no `.frob/perf/`
artifacts yet / no duplicated spawn shape: zero findings, not zero
checking). Broader
conceptual and mechanical-sympathy background these lexical rules draw
from -- including which smells are `STATIC` (linter-shaped like the table
above), `PROFILE`-only, or `ADVISORY` -- lives in
`docs/design/coding-performance-corpus.md`. Waivable per-site
with reason, as always (`frob:waive PERF005 reason="..."`), or -- for
PERF005/PERF006 specifically -- proven with a reasoned termination
directive instead of a blanket waiver (see below).

## Recursion: prove-terminating-or-error (PERF005/PERF006, T-0290)

Termination is undecidable in general, so PERF005/PERF006 stay SOUND, not
complete: they prove the decidable fragment and ERROR on everything else,
per the same "prove it, or justify it at the code" philosophy T-0289 uses
for arch complexity overrides.

- **Detect**: `frob.perf._recursion` builds a small same-file, name-based
  call index (self-calls and A<->B mutual recursion) over
  `RawSymbol.body_tokens` -- the same best-effort lexical posture as
  PERF001-004, and deliberately a separate graph from
  `frob.graph.callgraph` (T-0288's dup-inlining substrate), which excludes
  self-edges and public callees by construction for a different purpose.
- **Prove-or-error**: a recursive call is considered proven only when the
  function both (a) narrows its argument toward a base case on a
  well-founded measure -- a decreasing bounded integer (`n - 1`, `n // 2`)
  or structural descent (`.next`/`.left`/`.right`/`.parent`, a one-sided
  slice) -- and (b) contains a guard (`if`) that can reach a base case.
  Anything short of that is PERF005: unproven termination, ERROR.

  <!-- frob:invariant INV-018 -->
- **Escape hatch**: `frob:invariant terminates reason="..." measure="..."`
  at the recursive symbol's site is the reasoned, auditable override --
  both `reason` and `measure` must be non-empty to count as proof. This is
  the same comment DSL every other `frob:invariant` anchor uses
  (docs/modules/graph.md#comment-dsl); it does not require a matching
  `invariants/INV-###.md` file.
- **Depth/stack safety (PERF006)**: a tail-recursive call (`return f(...)`
  as the last thing on a path) is flagged separately from PERF005 -- Python
  has no TCO, so tail recursion over runtime-sized input is a stack-
  overflow/DoS bug, not just an unproven-termination finding. The same
  `frob:invariant terminates reason="..." measure="..."` directive silences
  PERF006 too (a proven depth bound is also a proven termination measure).

## Cross-stage redundant recomputation (PERF007, T-0413 -- the PERF META-GAP)

PERF001-006 all reason about ONE function body at a time -- lexical
linear-scan smells, or a recursive function's own termination proof. None
of them can see the class of waste that actually dominated a real `frob
check` run this repo shipped: the SAME expensive computation
(`frob.lang._parse`) invoked repeatedly, from DIFFERENT top-level
functions/stages, on the same kind of input, with no shared cache -- 168s
of redundant CPU across an entire `frob check` invocation that PERF never
flagged, because it never looked ACROSS call sites. T-0423's run-scoped
memoization (`frob.check._memo.memoize_per_run`) fixed the concrete
incident; PERF007 is the enforcement so a NEW instance of the same class
(a different expensive function, called from two different stages, again
uncached) is caught statically instead of waiting for a second profiling
incident.

Config-driven, generic, project-agnostic (the same posture as
`frob.gates._docblocks`'s `[[docblocks.commands]]` -- never a hardcoded
per-project "these are frob's expensive functions" list): `frob.toml`'s
`[[perf.heavy]]` array names each call target this project considers
expensive enough to deduplicate:

```toml
[[perf.heavy]]
name = "parse_file"
cached_by = ["memoize_per_run", "lru_cache", "cache"]
```

`name` is the bare call-target identifier as it appears in a call
expression's token stream (matching every other PERF rule's token-level,
not import-resolved, posture). `cached_by` (optional, defaults to
`memoize_per_run`/`lru_cache`/`cache`) lists decorator names that, found
immediately above `name`'s own `def`/`fn` in this project's tracked
sources, mean a shared cache already exists.

Detection (`frob.perf._redundancy.redundant_computation_violations`, pure,
over the already-parsed token stream -- no re-parsing): every top-level
`FUNCTION`/`METHOD` symbol's `body_tokens` is scanned for a `<heavy-name>
(` call-site pattern. If a heavy name is called from 2+ DISTINCT top-level
symbols (a real cross-call-site repeat -- two calls inside the SAME
function are that function's own business, not PERF007's concern) and its
own definition carries none of `cached_by`'s decorator names, every call
site beyond the first fires PERF007 naming both the redundant site and the
first one it duplicates. No `[[perf.heavy]]` entries at all means zero
PERF007 checking -- fail-open, same posture as every DOC004 namespace/
command source.

Acceptance (T-0413's own wording): a fixture where two functions both call
an uncached configured target is flagged; a fixture where only one
function calls it (or the target is `@memoize_per_run`-decorated) is not
-- see `tests/test_perf.py::TestPerf007RedundantComputation`.

## Shared interprocedural effect-summary substrate (`EffectGraph`, T-0922)

T-0775 (PERF008) and T-0919 (PERF012) each needed to answer "does calling
this function, however many hops deep, reach an expensive effect" --
T-0919 built that as `_EffectGraph.summary(symref)` inside PERF008's own
`_loop_effects.py` module, since PERF008's reachability graph was already
the right shape to extend. T-0922 promotes that graph OUT into its own
module, `frob.perf._effect_summaries`, with `EffectGraph` as a
first-class, documented public surface -- every PERF rule that keys on a
sub-call effect (PERF008, PERF012, and any future rule) is meant to
consume ONE `EffectGraph` instance rather than hand-roll its own
call-graph walk.

**What it answers**, for any function/method symbol in a set of parsed
files:

- `EffectGraph.reachable_effect(name)` -- the cheap yes/no/first-hit
  question PERF008 asks: does calling something named `name`
  transitively reach ANY directly-effectful call (a process spawn or
  directory walk, today's two effect classes)?
- `EffectGraph.summary(symref)` -- the FULL per-function EFFECT-SUMMARY:
  every `(kind, arg)` pair transitively reachable by calling `symref`,
  however many hops deep, propagated through sibling/cousin callees and
  diamonds alike.

**Direct effect detection**: a call is directly effectful if its own
dotted callee matches a small, hand-picked process-spawn table
(`subprocess.run/Popen/call/check_call/check_output`, `os.system/
popen/spawn*`, a bare imported `Popen(`) or directory-walk table
(`os.walk`, `os.scandir`, `glob.glob/iglob`, any receiver's `.rglob`/
`.iterdir`) -- narrower than `frob.vet._capability_registry`'s full
"exec"/"fs" capability kinds, since this ticket only ever asks about
spawn/fs-walk, not bare file read/write.

**Transitive call-graph reachability**: a SECOND, local, whole-project,
name-based call graph, deliberately not `frob.graph.callgraph.
build_call_graph` -- that graph only ever resolves PRIVATE callees, by
design, to stop its BFS at the public-API boundary. The real T-0773
incident crosses exactly that boundary (the spawn lives behind a PUBLIC
`run_argv`), so this graph resolves every candidate, public or private,
bounded to 8 hops / 200 nodes, matching `frob.perf._recursion`'s own
precedent for building a second graph rather than widening `callgraph`'s
contract for a use case it was not designed for. Multi-hop depth is
opaque to a consuming rule by construction: a spawn 2, 3, or more hops
below the analyzed function fires identically to a direct occurrence --
see `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect
.test_loop_invariant_spawn_call_three_hops_deep_is_flagged` and
`tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.
test_three_hop_duplicate_split_across_sibling_callees_is_flagged`.

**Argv-equivalence facts propagate across sibling callees**: `summary`'s
`(kind, arg)` occurrence set is unioned across every resolved candidate
callee at every hop, so a duplicate split across two entirely different
sibling/cousin call chains (not just two direct calls in the same
function) is still caught as the SAME occurrence -- the comparison key is
whitespace-normalized argument TEXT, not source-position, so
independently-formatted-but-identical argv is recognized as equivalent.

**Explicit Unknown, not silent empty (T-0922 criterion (c))**: a call
this substrate cannot bind -- dynamic dispatch, an external/stdlib
boundary with no local definition, an ambiguous short name with no
same-file or unambiguous cross-file candidate, an unrecoverable argument
list, or a summary walk that gives up on its recursion/budget limit --
now appends an explicit `(UNKNOWN_KIND, Unknown(reason))` member to the
occurrence set instead of silently contributing nothing. `Unknown`
compares equal to nothing but itself (plain identity, deliberately not
overridden), so it can only ever WIDEN what a rule can see (a caller can
ask "did any part of this give up?"), never manufacture a false-positive
match under a duplicate-detection consumer's equality-keyed grouping.
Each consuming rule documents its OWN Unknown policy (below).

See `tests/unit/perf/test_effect_summaries.py` for the substrate's own
unit-level guarantees (`Unknown`'s identity-only equality, an ambiguous
cross-file callee degrading to an explicit `Unknown`, a fully-resolvable
path carrying no spurious `Unknown`).

**Structural twin**: the `.strata` REL310/REL311 interactive-cost-bound
obligation (`frob.strata._interactive_cost`, T-0919's sibling family)
asks a related but NOT directly-wireable question -- whether a
human-facing node's cost is bounded/deduplicated -- over strata's own
declarative node/attr graph, not python call-graph facts. It cannot
consume `EffectGraph` directly (different domain: presence-of-a-declared-
attr over a `.strata` node graph, vs. a python AST call graph), but the
INCIDENT both families generalize from is the same one (T-0919's doubled
`frob check` subprocess spawn), and REL311's own `_BOUNDED_COST_TOKEN_RE`
proof-of-discharge scan is a plainer-grained analogue of what this
substrate does with real precision -- a future `.strata` conformance rule
wanting real cross-python-call-graph evidence (rather than a token-regex
proxy) is the natural place to wire the two together; noted here rather
than wired, since `src/frob/strata/**` is out of this ticket's scope.

## Loop-invariant effectful call detector (PERF008, T-0775)

Motivated by the 2026-07-22 rev-parse incident (T-0773): `frob ticket
list` spawned `git rev-parse --git-common-dir` dozens of times because
the LOOP (one iteration per ticket row) and the EFFECT (a subprocess
spawn, three calls deep through `frob.gitio.run_argv`) live in different
modules -- no per-function syntactic PERF heuristic (PERF001-004, each
scoped to one function body) can see this shape.

Detection (Python only for now -- an accepted scope cut matching
PERF001-004's existing python-first tiering, tracked as `frob:todo
T-0775` in `frob.perf._loop_effects`'s module docstring): for each `for`/
`while` loop, for each call site lexically inside it (attributed to its
innermost enclosing loop when loops nest), if the call is directly or
transitively effectful (via `EffectGraph`, above) AND its argument list's
identifiers never include the loop's own bound variable(s) or a name
assigned anywhere in the loop body, PERF008 fires naming the call site,
the effectful callee, and the loop-invariance reasoning. WARN-tier by
default, not ERROR: undecidable invariance leans toward firing (recall
over precision, same repo philosophy as PERF007), so a `frob:waive
PERF008 reason="..."` is always available for a deliberate re-read
(freshness under concurrency is a real, legitimate reason to re-run an
effect every iteration).

**Unknown policy**: PERF008 only ever asks `EffectGraph.
reachable_effect(name)`, the cheap yes/no/first-hit question -- an
unresolvable or ambiguous callee name simply yields "no effect found via
this name", so an unresolvable binding can only ever produce a MISSED
finding here, never a false one and never a crash. PERF008 does not
consume `summary`'s richer, argument-carrying `Unknown` members at all.

See `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect`
for the true-positive (transitive spawn 2 and 3 hops deep, direct
fs-walk, the real T-0773 ticket-row shape) and false-positive
(loop-varying argument, unresolvable/external callee) cases.

## Duplicate-identical-subprocess-spawn detector (PERF012, T-0919)

Motivated by the `frob ticket done-report` two-full-check-spawns incident
(T-0919): `_check_gates_summary_fn`/`_check_gate_findings_fn` (`frob.app.
ticket_runner`) each independently spawned their OWN full `python -m frob
check --ticket <id>` subprocess -- textually IDENTICAL argv and kwargs --
from the SAME calling function, serially, doubling an already-slow
(600s-timeout) foreground cost for output fully re-derivable from a
single run. PERF008 does not catch this shape: it only fires on a
loop-invariant effectful call INSIDE a loop; this is a duplicated effect
reachable from two call sites in ONE function body, no loop involved.

**Interprocedural by construction**: PERF012 does not hand-roll its own
call graph. It reuses `EffectGraph.summary(symref)` (above) -- the SAME
shared substrate PERF008 builds -- for the FULL transitively-reachable
`(effect_kind, arg)` multiset for any function, however many calls deep,
propagated through sibling callees, cousins, and diamonds alike
(cycle-safe, budget-bounded). `f()` calling `g()` calling `h()` which
spawns, where `f()` ALSO calls `i()` calling `j()` which spawns the SAME
argv, is caught exactly like two direct sibling calls in `f()` would be.

Detection (Python only, same python-first tiering as PERF001-004/PERF008):
for each function/method `F`, every call site UNCONDITIONALLY inside `F`'s
own body (excluding anything nested inside an `if`/`try`/`with`/loop/
`match` -- a call gated behind a conditional is not comparable the same
way; a `try`/`except` fallback is by definition mutually exclusive with
the path it falls back FROM, never a genuine duplicate) is resolved to its
occurrence set (itself directly, if it IS a spawn/fs-walk call, else the
`summary(...)` of its resolved callee). Callee name resolution is SCOPED
to same-file candidates first (`EffectGraph.resolve_scoped`), falling
back to a project-wide match only when unambiguous -- an early version of
this rule unioned every same-named candidate project-wide unconditionally,
which cross-contaminated unrelated call paths through common short names
(`run`, `check`) and produced thousands of false positives; scoping this
resolution was the fix. If two or more of `F`'s own call sites end up with
the SAME occurrence, PERF012 fires once per `F`, naming the duplicate
lines and the shared argument shape. WARN-tier, waivable (`frob:waive
PERF012 reason="..."`) for a genuinely deliberate independent re-run.

**Unknown policy**: an unresolvable call site now yields an explicit
`(UNKNOWN_KIND, Unknown(reason))` occurrence (T-0922) instead of silently
contributing nothing. Because PERF012's grouping key is `(kind, arg)`
equality and `Unknown` never equality-matches ANYTHING (not even another
`Unknown`), an `Unknown` occurrence can never itself pair up with
anything else and can never manufacture a duplicate finding -- it can
only ever ADD visibility ("this call path has an unresolved edge"),
never a false positive. `_def_violations` additionally skips `UNKNOWN_
KIND` outright when grouping, as a belt-and-suspenders guard against a
future accidental equality collision.

PERF012 inherits BOTH the spawn AND directory-walk needle tables
`EffectGraph` already defines in `_effect_summaries.py` -- widening those
tables (network calls, heavy parses) is a shared follow-up both rules
gain simultaneously (`frob:todo T-0919` in `frob.perf._dup_spawn`'s
module docstring).

See `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn` for the
true-positive (two sibling helpers, the two/three-hop multi-hop-via-
different-callees cases) and false-positive (call-site-varying
arguments, single call site, unresolvable dynamic-dispatch callee) cases.

**T-1018 calibration (1777 -> 0 repo findings)**: the T-0922 EffectGraph
substrate expansion made PERF012 genuinely interprocedural (correct, by
design) but also exposed two false-positive classes that did not exist at
the T-0919 20-finding baseline, both fixed in the SAME detector pass:

1. **Before/after state-check interleaving** (`_dup_spawn._split_clean_runs`):
   two call sites sharing an occurrence are only a real "paid for the same
   thing twice" duplicate when NOTHING effectful happens between them. The
   single largest observed cluster was a `git rev-parse HEAD`-before,
   mutate, `git rev-parse HEAD`-after idiom (`tests/test_ticket_land.py`'s
   `_rev_parse`/`_apply_gate_rule_sync` shape) -- a legitimate state-change
   assertion, not redundant recomputation. A call site whose own reachable
   effect is a clean SINGLETON (exactly this one occurrence, nothing else)
   still groups with its neighbors exactly as before; a call site that
   reaches this occurrence ALONGSIDE something else (multi-effect, or an
   `Unknown` member) now breaks the run instead of silently bridging it.
2. **Splat-forwarding wrapper conflation** (`_effect_summaries._contains_splat`):
   a generic pass-through helper (`def _git(*args, cwd): subprocess.run(
   ["git", *args], cwd=cwd)`) has ONE fixed source text at its own
   definition site regardless of what any given caller forwards through
   `*args`/`**kwargs` -- two callers passing completely different real argv
   (`_git("add", ...)`, `_git("commit", ...)`) both resolved to this SAME
   wrapper and looked like a textually-identical duplicate spawn. A direct
   effect call whose argument list contains a splat anywhere in its
   subtree (including nested inside a literal, e.g. the `*args` inside
   `["git", *args]`) now degrades to an explicit `Unknown` instead of a
   comparable literal arg-text occurrence -- it can widen visibility but
   can never manufacture a false duplicate the way `Unknown`'s identity-
   only equality already guarantees elsewhere in this substrate.

Both fixes are conservative in the SAME direction as the rest of this
substrate (degrade toward missing a duplicate, never toward manufacturing
one) and neither touches the T-0919/T-0922 true-positive fixtures (a
plain named-parameter forward like `check_gates(root, ticket_id)` ->
`subprocess.run([..., ticket_id], ...)` still fires: it has no intervening
effect and no splat). See `tests/unit/perf/test_dup_spawn.py::
TestPerf012DuplicateSpawn` for the T-1018 regression tests (both FP
classes plus a true-positive guard proving the interleaving fix does not
touch adjacent-duplicate detection) and `tests/unit/perf/
test_effect_summaries.py::TestSplatArgumentDegradesToUnknown` for
`_contains_splat`'s own unit coverage.

## The killer join: hot AND quadratic

`frob perf heat --smells` intersects the two signals: symbols ranked by
profiled time that ALSO carry PERF findings. That intersection is the
malmberg fix generator -- the static rule says "this scan has a better
data structure", the profile says "and it is actually where the time
goes". Ranked output, remedy per row.

## Hot-graph collector (T-0710, EPIC T-0709)

`frob.perf._hotgraph`/`frob.perf._sampler` add a SAMPLING profiler
alongside the existing deterministic cProfile pipeline above -- lower
overhead, and (the point of this ticket) a hit-stream contract that is
LANGUAGE-NEUTRAL BY CONSTRUCTION, so a non-python collector can feed the
same downstream sketch store/advisories (T-0711/T-0712) without touching
this module.

- **The stream contract.** A `SampledStack` is nothing but a tuple of
  `SampledFrame(file, line, weight)`, innermost frame first. Nothing
  python-specific leaks into it -- a native/perf, V8, or JVM collector
  adapter (T-0748, below) produces the identical shape from its own
  profile format, mirroring `frob.arch._normalized.LanguageAdapter`'s
  per-grammar pattern.
- **The resolver.** `build_section_index(modules: list[NormalizedModule])
  -> SectionIndex` derives one `Section` per function/method body and per
  loop/branch body nested inside one, purely from `NormalizedFunction`/
  `NormalizedLoop`/`NormalizedBranch` line fields -- no `frob.lang`/
  tree-sitter access, so it works identically on a python, TypeScript,
  rust, kotlin, or cpp module's normalized tree. `NormalizedFunction`
  already carries a real `(line, body_line_count)` span; `NormalizedLoop`/
  `NormalizedBranch` carry only an anchor line in a FLATTENED sibling list
  with no nesting info (T-0609 never needed more). DEGRADE-TO-CORRECT
  (round-2 review fix, replacing a round-1 next-sibling-boundary guess
  that silently mis-attributed a loop-body sample AFTER a nested branch
  to that branch): a block gets an EXTENDED span (to the function's end)
  only when it is PROVABLY the function's only loop/branch -- nothing else
  competing for the remaining lines. The instant a function has 2+
  loops/branches, every block in it degrades to a single-line span (its
  own anchor line only), and any other line in that function resolves to
  the enclosing FUNCTION section instead of a guessed sibling -- coarser,
  never wrong. See `frob.perf._hotgraph._block_sections`'s docstring for
  the full mechanism. `resolve_stream(index, stacks) -> HitStream`
  matches each stack's leaf frame against the innermost (smallest-span)
  matching `Section`; a leaf matching nothing resolves to
  `UNATTRIBUTED_SECTION_ID` -- NEVER dropped, always a visible
  `SectionHit` (`HitStream.unattributed_weight` sums exactly these), so a
  caller can always account for 100 percent of sampled weight. Call edges
  come from the leaf's caller frame (`frames[1]`): `is_external=True` when
  the caller resolves to a section but the leaf callee does not (a stdlib/
  third-party callee this repo's normalized model never modeled).
- **The python sampler.** `StackSampler` (in `frob.perf._sampler`) runs a
  background daemon thread that snapshots EVERY LIVE THREAD's frame via
  `sys._current_frames()` every `SamplerConfig.interval_s` (10ms default),
  converting each snapshot into one `SampledStack` per thread -- the py-spy-
  style fallback backend. T-0948: this already covers any `ThreadPoolExecutor`
  worker thread spawned from the same interpreter (`sys._current_frames()`
  is process-wide, not caller-thread-scoped) -- see "Pool-dispatched work
  attribution" below for the half of this it does NOT cover
  (`ProcessPoolExecutor`, a separate interpreter) and how the profiling
  harness addresses that. On python 3.12+, `sys.monitoring` (PEP 669)
  is the lower-overhead backend of choice (checked via `hasattr(sys,
  "monitoring")`, `_HAS_SYS_MONITORING` in `_sampler.py`); this repo's
  pinned minimum interpreter is 3.11 (`requires-python = ">=3.11"`), so
  the background-thread backend is what actually runs today -- the
  version check is there so a future interpreter bump upgrades backends
  automatically, no call-site change needed.
  Measured overhead (`tests/unit/perf/test_hotgraph.py::TestStackSampler.
  test_overhead_under_five_percent`, a fixture hot-loop workload run
  unsampled vs sampled at the 10ms default): **well under the 5 percent
  budget** -- see that test's assertion and its recorded ratio in the
  T-0710 Done report; a background thread waking every 10ms to read one
  frame snapshot is orders of magnitude cheaper than the workload's own
  hot loop.
- **Harness composability.** `run_sampled(fn, config) -> (list[SampledStack],
  elapsed_s)` brackets a workload exactly the way `frob.perf._profile`
  brackets `cProfile.Profile.enable`/`disable` -- `StackSampler.start`/
  `stop()` around the call -- so it drops into the same run-a-callable
  shape the existing harness (`frob.perf._harness.main`) and `frob test`'s
  python runner both already use, without a second execution model. No CLI
  subcommand (<!-- frob:waive DOC006 reason="proposal syntax for a not-yet-built flag, the same sentence discloses it does not exist yet" -->`frob perf profile --sampled`) or `frob test` flag exists
  yet -- that surface, and feeding `resolve_stream`'s `HitStream` into a
  persisted store, are T-0711/T-0712's job; this ticket ships the
  language-neutral contract, resolver, and a harness-composable python
  producer for them to build on.

T-0972: `build_section_index`'s own per-module `sections.sort(...)` and
`language_deciles`'s own per-language `sorted(entries, ...)` calls each
picked up a reasoned `frob:waive PERF004` (both differ per module/
language, nothing to hoist); `StackSampler`'s per-tick live-thread scan
picked up a reasoned `frob:waive PERF003` (bounded by thread count, not
a scale-sensitive cross join) -- no behavior change.

## Pool-dispatched work attribution (T-0948)

`frob check`'s own gate dispatch (`frob.gates._run_combined_jobs`) fans
CPU-heavy gates onto a `ProcessPoolExecutor` and the rest onto a
`ThreadPoolExecutor`. Neither of the three collectors above used to see
that work: a `cProfile.Profile` enabled in the profiling harness's own
process/thread has no visibility into a separate spawned interpreter, and
`StackSampler` used to record only the thread that called `start()`. The
T-0928 audit measured this directly: profiling a real `frob check` run
resolved roughly HALF its wall time to `frob perf heat`'s "unattributed"
bucket (237 symbols attributed, 30.349s unattributed of a ~60s artifact).

Two independent fixes, one per collector family:

- **`StackSampler` now samples every live thread** (this process only),
  not just the calling one -- see the sampler bullet above. This alone
  makes `ThreadPoolExecutor`-dispatched work visible with zero changes to
  `frob.check`/`frob.gates`' own dispatch code, since a worker thread it
  spawns is still a thread of the SAME interpreter `sys._current_frames()`
  already enumerates.
- **`frob.perf._serial_pools.install_serial_pools()`**, called by default
  from the profiling harness (`frob.perf._harness.main`, opt out via
  `FROB_PERF_SERIAL_POOLS=0`), replaces both `ThreadPoolExecutor` and
  `ProcessPoolExecutor` with `SerialExecutor` -- a same-thread, same-
  process drop-in that runs every submitted job immediately, inline, on
  the calling thread -- for the duration of the profiled subprocess only.
  This turns EVERY pool-dispatched job (including the `ProcessPoolExecutor`
  half a same-process sampler still cannot see) into ordinary, fully
  visible call stack under whatever `cProfile`/`StackSampler` instrument
  is already running. It is the documented "serial diagnostic mode" fix
  direction the T-0948 ticket named: a profiling pass trades real
  wall-clock parallelism for complete CPU-time attribution, which is
  exactly the trade a profiling pass wants. Implemented entirely inside
  `frob.perf` (monkeypatching `concurrent.futures`'s pool-executor names,
  both the `concurrent.futures.ThreadPoolExecutor(...)` attribute-access
  call shape `frob.check` uses and the `from concurrent.futures import
  ThreadPoolExecutor, ProcessPoolExecutor` bound-name shape `frob.gates`
  uses) -- no change to `frob.gates`/`frob.check`'s own dispatch code, so
  production `frob check` runs keep their real parallelism unconditionally.

## Hot-graph sketch store (T-0711, EPIC T-0709)

`frob.stats._sketch`/`frob.perf._sketch_store` are the persisted-store half
of T-0710's hit-stream contract, per that ticket's plan: feed
`resolve_stream`'s `HitStream` into a cross-run, size-bounded quantile
store, without ever storing raw samples or precomputed quantiles.

- **The sketch.** `QuantileSketch` (`frob.stats._sketch`) is a DDSketch-
  style log-bucket histogram: values are mapped onto log-scale buckets
  sized so every value landing in a bucket is within `alpha` relative
  error of that bucket's read-time point estimate, regardless of the
  input distribution's shape -- unlike a moment-based sketch (t-digest),
  which can be misled by a multi-modal distribution, DDSketch is exact
  per-bucket by construction. `add_value`/`merge_sketches`/`decay_sketch`
  each return a NEW sketch (frozen pydantic, matching this project's
  value-type convention); `quantile(sketch, q)` computes any quantile at
  READ time, walking bucket weights -- nothing is ever stored pre-
  aggregated. Buckets are a sparse `dict[int, float]`, so a sketch over a
  small number of distinct magnitude clusters (the bimodal 1ms/100ms
  acceptance fixture) stays a handful of entries -- serialized well under
  1KB regardless of sample count.
- **The store.** `frob.perf._sketch_store` persists one `QuantileSketch`
  per hot-graph section in `.frob/hotgraph_sketches.db` (sqlite, one
  `sketches` table, `section_key -> (kind, last_used, payload)`).
  `put_sketch` implements the ticket's decayed-merge update rule exactly:
  `prior' = merge(current_run_sketch, decay(stored_prior,
  half_life_runs))` -- one decay step per write, so `half_life_runs`
  really means "runs", not wall-clock time. `store_size_bytes`/
  `_evict_coldest` enforce `[perf.sketch].store_cap_bytes` (~100KB
  default) by dropping the least-recently-used section first, so the
  store structurally cannot grow to megabytes no matter how many distinct
  sections get sampled over the repo's lifetime.
- **Keying.** `stable_section_key` deliberately does NOT reuse
  `Section.id` (the resolver's own run-scoped id, `sha256(file, qualname,
  kind, start_line)`) verbatim -- that id changes the instant a line
  above a section drifts, even when the section's own content is
  unchanged, which would silently fragment a section's history across
  every unrelated edit elsewhere in the file. `Section.id`'s own
  docstring names this ticket as the layer responsible for a line-drift-
  tolerant key; `stable_section_key` accepts an optional `symbol_digest`
  (intended to be `frob.graph.digest.compute_digests`'s real,
  content-addressed symbol digest, once a future ticket wires it through
  the hot-graph resolver) and falls back to `section.file` when the
  caller has none yet -- still qualname/kind-precise, just not yet
  line-drift tolerant. Wiring the real digest through only changes which
  basis string gets hashed, not this module's schema, merge/decay logic,
  or eviction policy.
- **Config.** `[perf.sketch]` in `frob.toml` (`SketchStoreConfig`,
  loaded via `load_sketch_config`): `alpha` (DDSketch relative-error
  target, default 0.02 i.e. ~2 percent, per the ticket's plan),
  `half_life_runs` (default 5.0), `store_cap_bytes` (default 100_000).
  Fails open to defaults on a missing/malformed `frob.toml` or table,
  matching `frob.perf._redundancy`'s existing `[[perf.heavy]]` parsing
  posture.

**What this ticket did not wire.** No CLI subcommand or `frob test`
integration point calls `put_sketch` against a live `HitStream` yet --
that live-wiring (turning a `resolve_stream` output into per-section
`QuantileSketch`es and feeding them through this store on every profiled
run) is T-0712's job, mirroring T-0710/T-0748's own split between
"contract + resolver" and "live invocation". This ticket ships the
sketch algebra and the persisted, decayed, size-bounded store T-0712
calls into.

## Hot-graph consumers: query, advisories, ratchet (T-0712)

The consumer side of T-0710/T-0711's collector-and-store pair, wired
into `frob perf collect` (its only current producer) and `frob check`
(its only current gate consumer). `frob perf collect`
(`frob.app.perf_runner._persist_run`) now, for every `Section` its
resolved `HitStream` actually hit, builds a one-observation
`QuantileSketch` from that section's total run weight, writes it into
T-0711's store via `put_sketch` (keyed by `stable_section_key`, labeled
by `Section.qualname` for display), and reads the section's PRE-merge
prior via `get_sketch` first so the regression check below compares
old-vs-new, never a value the same call already overwrote.

### Hot-graph query surface (T-0712)

`frob perf hot [--path DIR] [--top N] [--by p90|p50xcount] [--json]`
(`frob.app.perf_runner._hot`, `frob.perf.list_sketches`) renders every
currently-stored section ranked by p90 or by p50 times total observation
weight (the default -- "moderately slow but frequent" outranks "rare
outlier"). A pure read of the store; running `frob perf collect` is what
populates it.

### Slow-operation advisories (T-0712)

`frob.perf._advisories`, suggestion tier, T-0332 discipline -- WARN,
never gated to error, always waivable -- computed straight off a
resolved `HitStream`/`SectionIndex`, no new IO:

- `external_call_advisories`: a loop section whose external call
  edge(s) sum to >= 50% of the loop's own total resolved weight ->
  batch/cache/hoist-out-of-loop, naming the dominating callee(s).
- `nested_loop_fanin_advisories`: a loop section reached from 2+
  distinct caller sections (a fan-in) that is also hot (>= 50% of its
  file's total resolved weight) -> complexity-suspect, naming the
  fan-in count.
- `heavy_tail_advisories`: a stored sketch whose `p90 / p50` ratio
  exceeds 3x -> variance advisory, naming a likely bimodal/outlier-
  driven mode.

T-0972: `external_call_advisories`'s own `sorted({callee for callee, _ in
edges})` message-formatting call picked up a reasoned `frob:waive
PERF004` (the callee set differs per section, nothing to hoist) -- no
behavior change.

### Regression ratchet (T-0712)

`frob.perf._ratchet` (PERF009): `check_ratchet` compares a section's
fresh current-run sketch against its stored prior at p50 and p90; a
relative shift beyond `[perf.sketch].ratchet_tolerance` (default 50%) at
either quantile produces a `RatchetFinding` naming the section and BOTH
decile sets (prior and current). `frob perf collect` persists every
run's findings to `.frob/perf/ratchet_findings.json`
(`save_ratchet_findings`, always overwritten whole, never appended);
`frob.gates.__init__.perf_gate` reads them back (`ratchet_violations`)
and surfaces each as a WARN-tier `PERF009` `Violation` -- gate-time is a
pure read of an already-recorded artifact, never a live re-collection,
matching every other PERF rule's static posture.

**What this ticket did not wire.** The MCP tool mirror the plan calls for
("QUERY: ... MCP tool mirror for agents") is NOT built here --
`src/frob/serve/_tools.py` is outside this ticket's declared scope
(`src/frob/perf/**`, `src/frob/app/**`, `src/frob/gates/**`,
`docs/modules/perf.md`); filed as a follow-up ticket rather than silently
expanding scope. A section's "current run" observation is presently a
SINGLE scalar (the run's total resolved weight for that section) rather
than a genuine within-run distribution over many individual call/loop-
iteration durations -- `HitStream.section_hits` carries one weight per
resolved SAMPLE, and per-sample weight is the sampler's fixed interval
for the python collector (T-0710), which would make a per-sample sketch
degenerate (all one value) rather than a real duration distribution; a
collector adapter whose samples carry genuinely varying weights (e.g. a
JFR-print duration-per-event import, T-0748) would make a richer
within-run sketch possible without changing this module's schema.

## Cross-language collector adapters (T-0748)

`src/frob/perf/_collectors.py` adds the per-language ADAPTER half the
T-0710 contract above was built to accept: three bounded parsers that
convert each ecosystem's own native profile format into the same
`SampledStack`/`SampledFrame` shape `resolve_stream` already consumes,
with zero changes needed to that contract.

- `parse_perf_script(text: str, source: str) -> Result[list[SampledStack], CollectorError]`
  -- Linux `perf record`/`perf script` textual output (frame-pointer or
  dwarf stacks), for native/Rust/C/C++ workloads, including the pyo3
  `strata_core`/`frob_core` crates in-process. A stack can carry mixed
  python+native frames; this adapter only resolves the native side (a
  frame with an `(file:line)` debuginfo suffix) -- a frame with no
  debuginfo (a python frame on the same stack, or a foreign module frame)
  gets `SampledFrame(file="", line=0)` rather than a guess.
- `parse_v8_cpuprofile(text: str, source: str) -> Result[list[SampledStack], CollectorError]`
  -- `node --cpu-prof` V8 `.cpuprofile` JSON (Chrome DevTools CPU profile
  format), for TS/JS. V8's `nodes` array only records child pointers, so
  this rebuilds the parent chain once so each sample's leaf node can walk
  up to a full stack; `lineNumber` is V8's 0-based convention, converted
  to this repo's 1-based `SampledFrame.line`. Hooks into the same vitest
  runner invocation the T-0587 collector already discovers.
- `parse_jfr_print(text: str, source: str, class_to_file: Mapping[str, str] | None = None) -> Result[list[SampledStack], CollectorError]`
  -- `jfr print --events jdk.ExecutionSample <file>` text output, for
  Kotlin/JVM. JFR's own frame shape carries only `(class.method, line)`,
  never a file path, so a companion helper resolves the file:
  `build_class_to_file(modules: list[NormalizedModule]) -> dict[str, str]`
  derives a class-name -> file map from the same `NormalizedModule`s
  `build_section_index` indexes. A class name seen in more than one
  module is ambiguous and is dropped from the map entirely (never
  guessed) -- an unmapped class's frame still parses, with `file=""`.

`CollectorError` (`ErrorSet`) is the shared failure type all three return
when a WHOLE profile is unparseable (never for one bad sample inside an
otherwise-good profile, which is logged and skipped instead):

- `BadPerfScript` -- `perf script` output has no recognizable sample
  blocks at all, or produced zero parsable stacks.
- `BadCpuProfile` -- the `.cpuprofile` text is not valid JSON, or is
  missing the `nodes`/`samples` keys the V8 format requires.
- `BadJfrPrint` -- the `jfr print` output has no `jdk.ExecutionSample`
  event blocks at all.

Every `Err` names the offending `source` file in its log line (NO-FAIL-
SILENT) -- a caller always knows which profile failed and why, never a
bare "parse failed".

**Unattributed-not-dropped frame policy.** Where a frame's true
`(file, line)` cannot be determined from the source format at all -- a
`perf` frame with no debuginfo, a JFR frame whose class has no
`class_to_file` entry -- the frame is still emitted, as
`SampledFrame(file="", line=0-or-n)`, rather than silently discarded.
`resolve_stream` can never match `file=""` to a real `Section`, so that
sample surfaces as visible `HitStream.unattributed_weight` instead of
vanishing or (worse) being guessed onto the wrong section -- the same
DEGRADE-TO-CORRECT discipline `frob.perf._hotgraph._block_sections`
documents for section-span resolution above.

**What this ticket did not wire.** `RunnerSpec.collector`
(`src/frob/testing/_models.py`, see
`docs/guides/extending/test-runner-entries.md#the-collector-field-t-0748`)
declares and validates which collector name attaches to a
`[[test.runner]]` entry, but no `frob test`/`run_selected` code path
invokes a named collector against a live run yet, and no `frob perf`
CLI subcommand shells out to real `perf`/`node`/`jfr` binaries end to
end -- both are live-invocation wiring, tracked separately as T-0765,
not a defect in this ticket's own collector-adapter scope.

## Public API

<!-- frob:describes src/frob/perf/_models.py::PerfError -->
<!-- frob:describes src/frob/perf/_models.py::ProfileArtifact -->
<!-- frob:describes src/frob/perf/_models.py::ProfileArtifact.pstats_name -->
<!-- frob:describes src/frob/perf/_models.py::ProfileArtifact.meta_name -->
<!-- frob:describes src/frob/perf/_models.py::HeatEntry -->
<!-- frob:describes src/frob/perf/_models.py::HeatReport -->
<!-- frob:describes src/frob/perf/_heat.py::join_smells -->
<!-- frob:describes src/frob/perf/_heat.py::render_bar -->
<!-- frob:describes src/frob/perf/_recursion.py::recursion_rules -->
<!-- frob:describes src/frob/perf/_redundancy.py::redundant_computation_violations -->
<!-- frob:describes src/frob/perf/_hotgraph.py::SampledFrame -->
<!-- frob:describes src/frob/perf/_hotgraph.py::SampledStack -->
<!-- frob:describes src/frob/perf/_hotgraph.py::SectionHit -->
<!-- frob:describes src/frob/perf/_hotgraph.py::EdgeHit -->
<!-- frob:describes src/frob/perf/_hotgraph.py::HitStream -->
<!-- frob:describes src/frob/perf/_hotgraph.py::HitStream.unattributed_weight -->
<!-- frob:describes src/frob/perf/_hotgraph.py::Section -->
<!-- frob:describes src/frob/perf/_hotgraph.py::build_section_index -->
<!-- frob:describes src/frob/perf/_hotgraph.py::resolve_stream -->
<!-- frob:describes src/frob/perf/_sampler.py::SamplerConfig -->
<!-- frob:describes src/frob/perf/_sampler.py::StackSampler -->
<!-- frob:describes src/frob/perf/_sampler.py::StackSampler.start -->
<!-- frob:describes src/frob/perf/_sampler.py::StackSampler.stop -->
<!-- frob:describes src/frob/perf/_sampler.py::run_sampled -->
<!-- frob:describes src/frob/stats/_sketch.py::QuantileSketch -->
<!-- frob:describes src/frob/stats/_sketch.py::new_sketch -->
<!-- frob:describes src/frob/stats/_sketch.py::add_value -->
<!-- frob:describes src/frob/stats/_sketch.py::merge_sketches -->
<!-- frob:describes src/frob/stats/_sketch.py::decay_sketch -->
<!-- frob:describes src/frob/stats/_sketch.py::total_weight -->
<!-- frob:describes src/frob/stats/_sketch.py::quantile -->
<!-- frob:describes src/frob/stats/_sketch.py::sketch_size_bytes -->
<!-- frob:describes src/frob/perf/_sketch_store.py::SketchStoreConfig -->
<!-- frob:describes src/frob/perf/_sketch_store.py::load_sketch_config -->
<!-- frob:describes src/frob/perf/_sketch_store.py::stable_section_key -->
<!-- frob:describes src/frob/perf/_sketch_store.py::get_sketch -->
<!-- frob:describes src/frob/perf/_sketch_store.py::put_sketch -->
<!-- frob:describes src/frob/perf/_sketch_store.py::store_size_bytes -->
<!-- frob:describes src/frob/perf/_sketch_store.py::new_run_sketch -->

```python
# frob/perf/__init__.py
def profile_command(argv: Sequence[str], root: Path) -> Result[ProfileArtifact, PerfError]
def load_artifact(root: Path, ref: str | None = None) -> Result[ProfileArtifact, PerfError]
    # ref=None loads the most recent artifact.
def heat(artifact: ProfileArtifact, snapshot: GraphSnapshot) -> HeatReport
    # Pure join of pstats rows onto symbol spans.
def perf_rules(snapshot: GraphSnapshot, files: Sequence[ParsedFile]) -> tuple[Violation, ...]
    # PERF001..PERF007; pure; consumed by the policy gate stage.

# frob/perf/_recursion.py
def recursion_rules(snapshot: GraphSnapshot, files: Sequence[ParsedFile]) -> tuple[Violation, ...]
    # PERF005 (unproven termination) + PERF006 (unbounded tail recursion).

# frob/perf/_redundancy.py
def redundant_computation_violations(root: Path, files: Sequence[ParsedFile]) -> tuple[Violation, ...]
    # PERF007: a frob.toml [[perf.heavy]]-configured call invoked from 2+
    # distinct top-level symbols with no shared cache.

# frob/perf/_heat.py
def join_smells(report: HeatReport, violations_by_ref: dict[str, tuple[str, ...]]) -> HeatReport
    # Attach PERF rule ids onto each entry -- the "hot AND quadratic" join.
def render_bar(cum_s: float, max_s: float, *, color: bool | None = None) -> str
    # ASCII '#'-block bar sized to cum_s/max_s for the CLI heat-map listing.

# frob/perf/_models.py
class ProfileArtifact(BaseModel):  # frozen; .frob/perf/<sha>.pstats + meta
    sha: str
    argv: tuple[str, ...]
    created: datetime
    total_s: float
    def pstats_name(self) -> str
        # Basename of the raw pstats file under .frob/perf/.
    def meta_name(self) -> str
        # Basename of the JSON meta sidecar under .frob/perf/.

class HeatEntry(BaseModel):        # frozen
    ref: str                       # symref
    cum_s: float
    self_s: float
    ncalls: int
    smells: tuple[str, ...]        # PERF rule ids attached to this symbol

class HeatReport(BaseModel):       # frozen
    entries: tuple[HeatEntry, ...] # ranked by cum_s desc
    unattributed_s: float          # time outside any known symbol

class PerfError(ErrorSet):
    SpawnFailed   = "Profiled command could not be started"
    NoArtifact    = "No profile artifact found; run frob perf profile first"
    BadArtifact   = "pstats artifact unreadable"

# frob/perf/_hotgraph.py -- language-neutral hit-stream contract + resolver
UNATTRIBUTED_SECTION_ID: str            # sentinel section id, never dropped

class SampledFrame(BaseModel):
    file: str
    line: int
    weight: float = 1.0

class SampledStack(BaseModel):          # innermost frame first
    frames: tuple[SampledFrame, ...]
    weight: float = 1.0

class Section(BaseModel):
    id: str                             # stable sha256-derived id
    kind: str                           # "function" | "loop" | "branch"
    qualname: str
    file: str
    start_line: int
    end_line: int

SectionIndex = dict[str, list[Section]]  # file -> sorted Sections

def build_section_index(modules: list[NormalizedModule]) -> SectionIndex
    # Function/loop/branch Sections, purely from NormalizedModule line fields.

class SectionHit(BaseModel):
    section_id: str
    weight: float

class EdgeHit(BaseModel):
    caller_section_id: str
    callee: str
    is_external: bool
    weight: float

class HitStream(BaseModel):
    section_hits: tuple[SectionHit, ...] = ()
    edge_hits: tuple[EdgeHit, ...] = ()
    def unattributed_weight(self) -> float
        # Sum of weight attributed to UNATTRIBUTED_SECTION_ID.

def resolve_stream(index: SectionIndex, stacks: list[SampledStack]) -> HitStream

# frob/perf/_sampler.py -- python StackSampler, the first stream producer
class SamplerConfig(BaseModel):
    interval_s: float = 0.01
    max_depth: int = 64

class StackSampler:
    def start(self) -> None
    def stop(self) -> list[SampledStack]

def run_sampled(fn: Callable[[], None], config: SamplerConfig | None = None) -> tuple[list[SampledStack], float]

# frob/stats/_sketch.py -- DDSketch-style log-bucket quantile sketch, T-0711
class QuantileSketch(BaseModel):  # frozen; alpha + sparse buckets + zero_count
    alpha: float = DEFAULT_ALPHA
    buckets: dict[int, float] = {}
    zero_count: float = 0.0

def new_sketch(alpha: float = DEFAULT_ALPHA) -> QuantileSketch
def add_value(sketch: QuantileSketch, value: float, weight: float = 1.0) -> QuantileSketch
def merge_sketches(a: QuantileSketch, b: QuantileSketch) -> QuantileSketch
def decay_sketch(sketch: QuantileSketch, factor: float) -> QuantileSketch
def total_weight(sketch: QuantileSketch) -> float
def quantile(sketch: QuantileSketch, q: float) -> float
def sketch_size_bytes(sketch: QuantileSketch) -> int

# frob/perf/_sketch_store.py -- sqlite decayed-merge sketch store, T-0711
class SketchStoreConfig(BaseModel):  # frozen; [perf.sketch] frob.toml table
    alpha: float = 0.02
    half_life_runs: float = 5.0
    store_cap_bytes: int = 100_000

def load_sketch_config(root: Path) -> SketchStoreConfig
def stable_section_key(section: Section, symbol_digest: str | None = None) -> str
def get_sketch(root: Path, section_key: str) -> QuantileSketch | None
def put_sketch(root: Path, section_key: str, kind: str, run_sketch: QuantileSketch, config: SketchStoreConfig) -> Result[QuantileSketch, PerfError]
def store_size_bytes(root: Path) -> int
def new_run_sketch(alpha: float) -> QuantileSketch
```

## Design decisions

- **Loop-context detection is lexical, one level deep -- and, as
  implemented, function-granularity.** `frob.lang`'s leaf-token stream
  (`RawSymbol.body_tokens`, `frob.lang._common._leaf_tokens`) is
  whitespace-insensitive by design (docs/modules/graph.md's digest contract
  depends on it), which means it also carries no line numbers and no
  block-nesting structure -- there is no INDENT/DEDENT leaf in tree-
  sitter's Python grammar to lean on. `perf_rules` therefore approximates
  "inside a for/while body" as "a `for`/`while` keyword appears earlier in
  the same function's token stream" rather than true block-scoped nesting,
  and every violation is reported at the *enclosing function's* span
  start, not the offending statement's exact line. This is a documented
  cut, not an oversight: a membership test written after a loop in the
  same function (but not inside it) can false-positive in principle;
  in practice this is rare because such code is unusual, and the
  container-kind gate below removes the dominant false-positive source.
  False negatives (a smell in a genuinely nested block the token stream
  can't distinguish from the outer one) are accepted over false
  positives.
- **PERF001/PERF002's container-kind check is Python-only and
  assignment-shape-based, not type-inferred.** `frob.perf._rules` tracks
  `name = [...]` (list) vs `name = {...}` / `set(...)` / `frozenset(...)`
  / `dict(...)` (set-ish) assignments textually within the same function.
  An identifier whose assignment shape isn't resolvable this way (e.g. a
  parameter, or a container built in another function) is never assumed
  to be a list -- PERF001/PERF002 simply do not fire on it. This is the
  false-positive-priority design point: silence on the unknown case, not
  a guess.
- **Coverage by language, exactly as implemented:**
  - Python: PERF001 (list membership), PERF002 (`.index()`/`.count()`),
    PERF003 (nested-loop equality), PERF004 (`sorted()`/`.sort()`) -- all
    four, first-class.
  - TypeScript: PERF001 (`.includes(`) and PERF002 (`.indexOf(`) only,
    both gated on the same function-level loop-token check but with *no*
    container-kind inference (the token stream carries no type
    information for this grammar) -- best-effort, higher false-positive
    risk than Python's PERF001/PERF002.
  - Rust: PERF001 (`.contains(`, standing in for `Vec::contains`) only,
    same best-effort posture as TypeScript.
  - PERF003 (nested-loop equality) is language-agnostic: it only counts
    `for` tokens and an `==` token, which both grammars' leaf-token
    streams carry identically.
  - PERF004 (`sorted`/`.sort()` hoisting) is Python-only; TypeScript's
    `.sort()` and Rust's `.sort()` are not currently distinguished from
    unrelated `.sort` identifiers in those grammars and are cut for 0.1.0
    rather than shipped as a false-positive-prone guess.
  - C and C++ are not covered: `frob.lang` supports parsing them, but
    docs/modules/perf.md's rule table has no C/C++ row (no idiomatic linear-scan
    literal to key off), so `perf_rules` never fires for those languages.
- **Size-blindness is why PERF defaults to warn.** The gate cannot know
  n=3 from n=28000; the heat-map join is what upgrades a warning into
  "fix this now". Promoting PERF to error is a per-repo choice.
- **Artifacts are content-addressed and per-worktree** (`.frob/perf/`),
  same posture as every other derived cache. Each `.pstats` file has a
  JSON meta sidecar (`ProfileArtifact.model_dump_json()`) at the same
  basename so `load_artifact` never has to re-derive argv/timestamp/total
  from the binary pstats format.
- **Python profiling first, runner-agnostic artifact model.** cProfile
  ships in the stdlib and covers frob's own ecosystem; sampling
  profilers for rust/ts are adapters later, not a redesign.
  `profile_command` strips a leading `python`/`python3` token from the
  caller's argv before handing it to `python -m cProfile -o <artifact>`,
  since cProfile already supplies the interpreter and would otherwise try
  (and fail) to parse `python` itself as the profiled script.
- **`--annotate` is function-granularity, not line-granularity, because
  cProfile is.** Unlike `line_profiler`, cProfile records one row per
  `(file, line, function)` triple where `line` is the function's
  *definition* line, not a per-statement counter. `frob perf heat
  --annotate <file>` therefore prints a `cum_s/ncalls` gutter only on
  each function's `def` line and a blank gutter on every other line --
  an honest reflection of what cProfile measures, not a fabricated
  per-statement number.

## Integration points

<!-- frob:describes src/frob/perf/_harness.py::main -->

`_harness.py` runs the profiled target as a subprocess entry point:

```python
# frob/perf/_harness.py
def main() -> int
    # Profile the target argv under cProfile, dump stats, and return the
    # workload's own exit code (not cProfile's, which is always 0).
```

- CLI: `frob perf profile|heat` (+ `--smells`, `--annotate`, `--json`).
- `frob check`: PERF rules run in the policy/gates stage at warn.
- Agents: implementer runs `frob perf heat --smells` when a ticket is
  perf-flavored; reviewer treats an introduced PERF001-at-error as a
  close blocker.
- T-0973: `main`'s `SERIAL_POOLS_ENV_VAR`/`_SAMPLE_ENV_VAR` env-var reads
  each carry a `frob:waive SEC110 reason="..."` -- both are behavior
  toggles (pool-serialization mode, stack-sampling opt-in), not secrets.
