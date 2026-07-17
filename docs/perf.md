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

Severity: `warn` by default (static size-blindness is real -- a 3-element
list is fine as a list); promotable per-repo via `[gates.severity]`
(`PERF001 = "error"`). Waivable per-site with reason, as always.

## The killer join: hot AND quadratic

`frob perf heat --smells` intersects the two signals: symbols ranked by
profiled time that ALSO carry PERF findings. That intersection is the
malmberg fix generator -- the static rule says "this scan has a better
data structure", the profile says "and it is actually where the time
goes". Ranked output, remedy per row.

## Public API

```python
# frob/perf/__init__.py
def profile_command(argv: Sequence[str], root: Path) -> Result[ProfileArtifact, PerfError]
def load_artifact(root: Path, ref: str | None = None) -> Result[ProfileArtifact, PerfError]
    # ref=None loads the most recent artifact.
def heat(artifact: ProfileArtifact, snapshot: GraphSnapshot) -> HeatReport
    # Pure join of pstats rows onto symbol spans.
def perf_rules(snapshot: GraphSnapshot, files: Sequence[ParsedFile]) -> tuple[Violation, ...]
    # PERF001..PERF004; pure; consumed by the policy gate stage.

class ProfileArtifact(BaseModel):  # frozen; .frob/perf/<sha>.pstats + meta
    sha: str
    argv: tuple[str, ...]
    created: datetime
    total_s: float

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

- **Loop-context detection is lexical, one level deep.** PERF rules see
  "inside a for/while body" and "inside a function invoked per-item in
  the same file" -- honest about not being interprocedural dataflow.
  False negatives accepted; false positives minimized by requiring the
  scanned collection to be loop-invariant where determinable.
- **Size-blindness is why PERF defaults to warn.** The gate cannot know
  n=3 from n=28000; the heat-map join is what upgrades a warning into
  "fix this now". Promoting PERF to error is a per-repo choice.
- **Artifacts are content-addressed and per-worktree** (`.frob/perf/`),
  same posture as every other derived cache.
- **Python profiling first, runner-agnostic artifact model.** cProfile
  ships in the stdlib and covers frob's own ecosystem; sampling
  profilers for rust/ts are adapters later, not a redesign.

## Integration points

- CLI: `frob perf profile|heat` (+ `--smells`, `--annotate`, `--json`).
- `frob check`: PERF rules run in the policy/gates stage at warn.
- Agents: implementer runs `frob perf heat --smells` when a ticket is
  perf-flavored; reviewer treats an introduced PERF001-at-error as a
  close blocker.
