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

Severity: PERF001-004 are `warn` by default (static size-blindness is real
-- a 3-element list is fine as a list); promotable per-repo via
`[gates.severity]` (`PERF001 = "error"`). PERF005/PERF006 are `error` by
default -- unlike the lexical smells, unreasoned unbounded recursion is a
control-flow hazard (T-0290), not a size-blind heuristic. PERF007 is
`error` by default and opt-in via config (see below) -- an unconfigured
project gets zero PERF007 checking, never a false positive from a guess
at what "expensive" means for it. Broader
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

## The killer join: hot AND quadratic

`frob perf heat --smells` intersects the two signals: symbols ranked by
profiled time that ALSO carry PERF findings. That intersection is the
malmberg fix generator -- the static rule says "this scan has a better
data structure", the profile says "and it is actually where the time
goes". Ranked output, remedy per row.

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
```

## Design decisions

- **Loop-context detection is lexical, one level deep -- and, as
  implemented, function-granularity.** `frob.lang`'s leaf-token stream
  (`RawSymbol.body_tokens`, `frob.lang._common.leaf_tokens`) is
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
