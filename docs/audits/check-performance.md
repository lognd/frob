# frob check end-to-end PERFORMANCE audit (T-0928)

MEASURE-FIRST, per T-0927's charter. All numbers below are measured on this
checkout's own worktree (`.claude/worktrees/agent-a7115e7e477d3fe43`, a
fresh merge of `main` at `a7834342`), natives built (`make core`), warm
`.frob/cache.db` (839 files, 0 parse misses on the runs below), via
`uv run frob` -- never a stale global install. Machine was idle for the
whole measurement pass per this ticket's own dispatch instruction.

## Method

Per the ticket's plan: dogfood this repo's own perf tooling
(`frob perf profile`/`frob perf collect --sampler`/`frob perf heat`,
docs/modules/perf.md) over a full `frob check` run, plus the per-stage
wall timings `gate-summary` already emits. The chunked `--only <group>`
loop (docs/guides/agent-playbook.md section 3b) is both the sanctioned
way to run `frob check` here AND, incidentally, the natural unit this
audit profiles stage-group by stage-group.

**Finding 0 (methodological, blocks the profile-first plan as written):
frob's own profiling stack cannot see inside `frob check`'s own gate
dispatch.** This was not assumed -- it was discovered by trying the
sanctioned method and reading its own output:

1. `frob perf profile -- -m frob check --only <group>` (cProfile,
   `frob.perf._profile.profile_command`) was run for every stage group.
   Every single run's `pstats` shows the SAME shape: the entire wall
   time collapses onto `{method 'acquire' of '_thread.lock' objects}` in
   the calling thread, with the orchestration call chain
   (`App.__call__` -> `run_check` -> `_run_tasks_concurrently` ->
   `_collect_results`) fully attributed and everything past that point
   invisible.
2. `frob perf heat --ref <sha>` (the joiner this audit is supposed to
   read hot symbols from) makes the same fact explicit in its own
   vocabulary rather than requiring inference: for the `gates-fast`
   artifact, `heat` reports **"237 symbol(s) attributed, 30.349s
   unattributed"** against a ~60s two-pass total -- i.e. `heat` itself
   already knows and reports that roughly HALF the profiled run resolved
   to nothing.
3. Root cause, read from `frob.check.__init__._run_tasks_concurrently`:
   gate jobs run on a `ThreadPoolExecutor` (I/O-bound/cheap gates) or a
   `ProcessPoolExecutor` (`_PROCESS_POOL_GATES`: archgate, sys, clones,
   perf, pii_structural, secrets, dead_symbols, protocol_summary,
   T-0415). `cProfile.Profile.enable()` instruments only the thread that
   called it; a `ThreadPoolExecutor` worker's frames are invisible to it,
   and a `ProcessPoolExecutor` worker is a SEPARATE INTERPRETER the
   profiler was never attached to at all. The calling thread just blocks
   in `future.result()` -> `Lock.acquire()`, which is exactly the one
   line every pstats dump above shows consuming the whole run.
4. `frob.perf._sampler.StackSampler` (the sampling backend `frob perf
   collect --sampler` and the harness's `FROB_PERF_SAMPLE` wiring both
   use) has the identical limitation by its own docstring: it "samples
   the CALLING thread's frame stack" only (`self._target_ident`). It
   would not see thread-pool or process-pool gate work either, if wired
   through `-m frob check` the same way (not attempted further once (1)
   and (2) already demonstrated the same blind spot from the deterministic
   collector; no reason to expect the sampling collector fares
   differently against the identical dispatch model).

**Consequence for this audit's method**: function-level attribution
INSIDE a concurrently-dispatched gate cannot come from profiling `frob
check` as one black box, no matter which of frob's own three collectors
is used -- that isolation has to happen by calling the gate's own
entry-point function directly, single-threaded, in-process (attempted
below for `test_gate`; see Finding 5). The ranked table below is
therefore ANCHORED on `gate-summary`'s own per-stage wall-clock brackets
(real elapsed time per named stage, unaffected by this blind spot --
`gate-summary` times each future around its own submit/complete, not via
cProfile) rather than on symbol-level `heat` output, with function-level
detail filled in from direct isolated calls and this repo's own prior
audit (docs/audits/perf.md, T-0410/T-0582/T-0423) wherever a stage's
internals were already isolated there and nothing since suggests they
changed shape.

## Measured wall time (2-3 runs per stage group, `--only` chunked)

```
lint          [ruff+ty]                             0.84s          (1 run)
static        [cycle,dup,arch,bind,exports]         22.79s / 22.96s (2 runs)
gates-native  [archgate,clones,perf,exhaustive]     35.22s / 16.63s (2 runs, HIGH VARIANCE -- Finding 3)
gates-security[sys,pii,secrets,dead,protocol]       11.95s / 11.79s (2 runs)
gates-fast    [drift,coverage,invariant,test,...]   30.65s / 30.80s / 30.66s (3 runs, STABLE)
```

Per-stage brackets from `gate-summary` (representative run, the numbers
the ranked table below is built from -- these did not vary meaningfully
run-to-run except where flagged):

```
gates-native:  archgate=11.08s  perf=9.50s   exhaustive_handling=1.20s  clones=0.00s
gates-security: sys=6.22s  pii_structural=4.60s  dead_symbols=3.53s  secrets=2.87s  protocol_summary=1.13s
gates-fast:    test=13.68s  coverage=5.04s  tickets=2.09s  refs=1.95s  invariant=1.80s
               registry=0.68s  walk_lint=0.85s  render_lint=0.65s  docblocks=0.40s
               doclink=0.10s  docanchor=0.05s  release=0.04s  fuzz=0.20s  (+ ~10 near-zero rows)
static:        no per-tool bracket printed (thread-pool tools, not `gate:` rows) --
               treated as one 22.9s bucket; frob-arch/frob-dup are the two heaviest
               by symbol count (76 warnings / 169 dup groups) and both do a
               repo-wide parsed-tree walk, same shape as archgate below (Finding 4)
```

Sum of all named rows above: ~91.4s. Every `--only` invocation also pays
a fixed graph-load tax independent of which gate ran (measured directly:
`build_graph(Path('.'), cache.db)` alone, fully cache-warm, 0 parse
misses, took **3.33s**) -- paid once per invocation in the chunked loop,
so chunking 5-ways here overcounts total CPU by roughly 4 x 3.33s ~= 13s
versus one true end-to-end run; a true unchunked `frob check` was not
run (this worktree is `FROB_AGENT`-gated same as any dispatched agent,
and a bare `frob check` correctly refuses per docs/guides/agent-playbook.md
section 3b -- not attempted, not worked around).

## Ranked hot-path table (>=80% of accounted runtime)

| # | Stage/function | s (repr. run) | % of 91.4s | cum % | class | justification |
|---|---|---|---|---|---|---|
| 1 | `static` bucket (cycle/dup/arch/bind/exports) | 22.9 | 25.1% | 25.1% | rust-candidate | thread-pool tools doing repo-wide parsed-tree walks (arch: SOLID/LSP/type-design over every symbol; dup: 169-group near-dup AST comparison); CPU-bound over the whole tree, same shape as archgate below |
| 2 | `test` gate | 13.68 | 15.0% | 40.0% | python-optimizable | `test_gate` (TEST001-015) runs entirely inside a thread-pool worker so cProfile could not attribute it in this pass (Finding 0); direct isolated call attempted (Finding 5) but did not complete in the time budget -- flagged, not closed |
| 3 | `archgate` gate | 11.08 | 12.1% | 52.2% | rust-candidate | repo-wide arch-rule tree-walk over every symbol; historically this repo's #1 dominator pre-T-0423 memo (docs/audits/perf.md H1, 91.5-153.6s), now memo'd down but still the single largest process-pool job |
| 4 | `perf` gate (PERF001-012 static rules) | 9.50 | 10.4% | 62.6% | python-optimizable | lexical token-stream scan (PERF001-009/012) over every function body in the repo; O(functions) with real per-function work (recursion proof, effect-graph BFS) |
| 5 | `sys` gate (SEC1xx capability scan) | 6.22 | 6.8% | 69.4% | io-bound | per-file capability scan (`scan_file_capabilities`); this repo's own T-0582 pass measured 592 files / 31.8s standalone, ~23s of which is `_python_binding_capabilities`'s O(candidates x kinds x needles) substring sweep (filed T-0829, unfixed) |
| 6 | `coverage` gate | 5.04 | 5.5% | 74.9% | python-optimizable | T-0410's pass found `_cov006` rescue helpers calling `frob.lang.parse_file` ~2000+ times per run (a 3rd instance of the redundant-parse class T-0413/PERF007 targets) -- unclear if since re-memoized; not re-verified this pass, see Disposition below |
| 7 | `pii_structural` gate | 4.60 | 5.0% | 79.9% | rust-candidate | per-file structural PII scan, same repo-wide-walk shape as archgate/sys; not previously isolated in docs/audits/perf.md |
| 8 | `dead_symbols` gate | 3.53 | 3.9% | 83.8% | rust-candidate | whole-graph reachability sweep over `GraphSnapshot`; graph-shaped work, same rust-candidate class as archgate |
| 9 | `secrets` gate | 2.87 | 3.1% | 86.9% | io-bound | per-file secret-pattern scan, same shape as `sys`/`pii_structural` -- these three gates likely share a walkable-file-set they could compute once (Finding 4) |
| 10 | `tickets` gate | 2.09 | 2.3% | 89.2% | python-optimizable | `tickets.md` ledger parse/validate over the full board; pure-python parse cost, not yet profiled in isolation |

Rows 1-8 already clear the ticket's 80% bar (83.8% cumulative); rows 9-10
included since they are this audit's top-10 remedy set.

## Top-10 remedy + estimated payoff

| # | Remedy | Est. payoff |
|---|---|---|
| 1 | `static` bucket: verify whether `frob-arch` (the `arch` tool) and the `archgate` GATE (#3) walk/parse the same file set independently -- if so this is a textbook PERF007 (T-0413) instance across a tool/gate boundary PERF007 does not currently reach (PERF007 only sees same-language call-site tokens, not tool-vs-gate duplication) | up to ~11s if the walks fully dedupe (archgate's own cost, paid twice) |
| 2 | `test` gate: finish the isolated `test_gate(...)` cProfile call this pass could not complete in budget (Finding 5) -- likely candidate: `_test003`'s alpha-interface derivation or `_test005`'s coverage cross-reference, both O(snapshot symbols) | unknown until isolated; flagged as the single largest UNRESOLVED row, highest-priority follow-up |
| 3 | `archgate`: already memo'd (T-0423); no further action unless a fresh isolated profile shows a new dominator distinct from the T-0410-era ones | ~0s further (already resolved once) |
| 4 | `perf` gate: PERF001-012's own token scan is O(functions); the `EffectGraph` BFS (PERF008/PERF012) is bounded (8 hops/200 nodes per docs/modules/perf.md) but runs per-candidate-loop, not memoized across candidates in the same file | investigate whether `EffectGraph.summary` is being rebuilt per-loop rather than once per file (a same-shape PERF007 candidate) |
| 5 | `sys`/`secrets`/`pii_structural`: three independent per-file scans, same file set, same shape (Finding 4/row 9) -- share ONE walk + ONE parsed-tree pass across all three instead of three separate `os.walk`/`glob` + parse passes | rough estimate: if 50% of each gate's time is walk/parse (vs scan logic), merging saves up to ~half of (6.22+4.60+2.87)=13.69s, i.e. ~6-7s |
| 6 | `coverage`: re-verify T-0410's `_cov006` ~2000-call `parse_file` finding under current code (T-0414's per-run memo may have already absorbed this; not confirmed this pass) | 0s if already memo'd, up to several seconds if not |
| 7 | `dead_symbols`: whole-graph reachability sweep -- check whether it re-derives a reachability set `archgate`/`coverage` already compute, vs a genuinely distinct traversal | investigate before assuming duplication |
| 8 | `gates-native` process-pool COLD-START variance (35.22s vs 16.63s on back-to-back runs, archgate/perf's own bracketed times nearly IDENTICAL both times) -- the ~18s delta is process-pool worker spawn + fresh cold import of `frob`/`frob_core`/`strata_core` per worker, not gate work | a warm/reusable process pool (or `--preload` import in the spawn bootstrap) could reclaim up to ~18s on a cold-cache invocation; needs isolating spawn-vs-work time directly (not done this pass) before sizing further |
| 9 | `tickets` gate: profile `tickets.md` parse/validate in isolation; not attempted this pass | unknown, likely small (2.09s absolute) |
| 10 | Profiling tooling itself (Finding 0): `frob perf profile`/`collect --sampler` cannot see thread-pool or process-pool gate work; a diagnostic "run gates serially, single-process, single-thread" mode (or per-worker `cProfile` attachment in the process-pool bootstrap) would let future passes profile gates 2-10 above directly instead of needing a bespoke isolated-call script per gate each time | not a runtime payoff -- an audit-velocity payoff; every future perf pass on this repo hits Finding 0 again without it |

## Finding 3: process-pool cold-start variance (gates-native, 35.22s -> 16.63s)

Two consecutive `--only gates-native` runs, same cache-warm repo state,
showed archgate/perf's own bracketed gate-summary times nearly identical
(11.09s/9.63s vs 11.08s/9.50s) while total WALL time differed by ~18s
(35.22s vs 16.63s). Since the bracketed per-gate times (the actual work)
did not move, the missing ~18s is orchestration/spawn overhead outside
any single gate's own timer -- consistent with `ProcessPoolExecutor`'s
`spawn` context (T-0415, `_open_process_pool`) building fresh worker
interpreters that cold-import `frob`/`frob_core`/`strata_core` on first
use per invocation. Not isolated further this pass (would need timing the
pool's own `__enter__`/first-submit latency directly); flagged as remedy
#8.

## Finding 4: three near-identical per-file security scans (sys/secrets/pii_structural)

`sys` (6.22s), `secrets` (2.87s), and `pii_structural` (4.60s) are three
distinct process-pool gates, each independently walking (a variant of)
the tracked source-file set and scanning file content. None of them were
found sharing a walk or a parsed-tree pass in this pass's reading of
`frob.gates.__init__`'s job table -- this is a candidate duplicate-walk
class, same shape as the T-0413 PERF007 gap (redundant CROSS-CALL-SITE
work), except the duplication here is cross-GATE at the file-set/walk
level rather than a single named function called twice. PERF007 as
specified today (`[[perf.heavy]]`, name-keyed call-site matching) would
not catch this shape -- it is looking for the SAME named call repeated,
not three DIFFERENT gates each doing their OWN walk over what happens to
be the same file set.

## Disposition: every generalizable anti-pattern, both-layers rule

| Anti-pattern | PERF00x detector | `.strata` obligation | Disposition |
|---|---|---|---|
| Same named expensive call, 2+ distinct top-level callers, uncached | PERF007 (exists, T-0413) | N/A (code-level, not a system-design obligation) | already covered; not a new gap this pass found evidence of beyond the still-open T-0829 (`sys` capability-scan cost, algorithmic not caching) and T-0830 (selfconform double-scan) from the prior audit |
| Cross-GATE duplicate file walk/parse (Finding 4: sys/secrets/pii_structural) | NOT COVERED -- PERF007 is name-keyed to one call target, not "N gates each independently walk file set F" | NOT COVERED | explicitly dispositioned: too structurally different from PERF007's shape to fold into it without redesigning PERF007's matching key from "named call" to "walked file-set identity"; needs its own ticket, not built here (audit-only scope) -- filed below |
| Process-pool cold-start overhead masquerading as gate cost (Finding 3) | NOT COVERED -- this is an orchestration cost, not a lexical code smell PERF00x's tree-sitter pattern engine can see | NOT COVERED -- not a code obligation, an infra-tuning question | explicitly dispositioned: out of PERF00x's design space (it detects source-level smells, not process-spawn scheduling); belongs in `frob.check`'s own dispatch tuning, ticketed separately |
| Profiler blind to thread-pool/process-pool dispatch (Finding 0) | NOT COVERED -- this is a gap in `frob.perf` ITSELF, not a target-codebase smell | NOT COVERED | explicitly dispositioned: this is a `frob.perf` capability gap (needs a new collector mode), not a PERF00x rule against target code; ticketed separately |

New tickets filed from this audit (all children of T-0927,
INVESTIGATE-OR-FIX, not blind-fixed, per this ticket's own audit-only
scope) -- see this ticket's Done report for the exact ids.

## Finding 5: `test_gate` isolated-call profile did not complete

Per Finding 0's plan, `test_gate(...)` was called directly (bypassing the
thread pool) via `_load_inputs(GateConfig(root='.'))` + a direct
`test_gate(...)` call under `cProfile`. `_load_inputs` alone completed in
4.46s (consistent with the graph-load tax). The direct `test_gate(...)`
call itself did not return within a 100s budget in this pass -- markedly
slower than the 12.36-13.68s `gate-summary` reports for the SAME gate
inside a real `--only test` run. This discrepancy (isolated call slower
than in-context call) was not root-caused this pass -- plausible
candidates are a `GateConfig(root='.')` default diverging from the real
check runner's config (e.g. ticket/base resolution taking a materially
different, more expensive code path with no active ticket bound), or a
missing warm cache the real run's `_load_inputs` call benefits from that
a fresh interpreter's `_load_inputs` does not. Reported as OPEN, not
closed -- row 2 of the ranked table and remedy #2 both carry this
forward rather than presenting a number that could not be reproduced.

## Remediation log (T-0929, quick wins from this audit)

**Row 10 (`tickets` gate, 2.09s, python-optimizable) -- FIXED.**
`tickets_gate` (`src/frob/gates/__init__.py`) dispatches eight TICK00x
rules; three of them (`_tick001_duplicate_ids`, `_tick003_stale_archive`,
`_tick006_phantom_filing`) each independently called
`frob.tickets._store.load_all`/`load_archive`, which re-reads and
re-parses the FULL `tickets.md`/`tickets-archive.md` ledger text from
disk on every call (no cache) -- 3 redundant `load_all` calls and 2
redundant `load_archive` calls per `tickets_gate` invocation, on top of
the `queue` `_load_inputs` had already built upstream. This is the same
"same expensive input recomputed N times, no shared cache" shape the
audit's meta-gap finding (E) describes, one level down inside a single
gate rather than cross-stage. Fix: `tickets_gate` now loads `active`/
`archived` ONCE and passes the `Result` values down to all three rules;
`_tick001_duplicate_ids`, `_tick003_stale_archive`, and
`_tick006_phantom_filing` no longer call `load_all`/`load_archive`
themselves.

Measured (`uv run frob check --only tickets`, same checkout, natives
built, warm cache, 2 back-to-back runs):

```
before (this audit's baseline): tickets=2.09s
after:                          tickets=1.10s / 1.13s
```

~46-47% reduction, consistent across both post-fix runs. Full
`tests/test_gates.py` (543 tests) passes unchanged.

**Row 4 (`perf` gate, 9.50s, python-optimizable) -- ALREADY RESOLVED,
verified not re-broken.** `perf_rules` (`src/frob/perf/_rules.py`)
already builds exactly ONE shared `_EffectGraph` for both PERF008 and
PERF012 (`shared_effect_graph = _EffectGraph(files)`, T-0919, landed
before this audit) -- the remedy this row asks to "investigate" is
already in place, and `EffectGraph.summary`/`reachable_effect`
(`src/frob/perf/_effect_summaries.py`) memoize per-symref (`self._memo`)
and per-file (`self._occurrence_cache`), so no per-loop rebuild exists to
fix. No code change made for this row; verified by reading
`perf_rules`/`EffectGraph` directly rather than assumed. Left as a
no-op, not silently skipped.

**Row 6 (`coverage` gate, 5.04s, python-optimizable) -- VERIFIED
ALREADY RESOLVED via the T-0414 parse memo, no code change.** Isolated
`coverage_gate(...)` call (bypassing the thread pool, mirroring Finding
5's method) with `frob.lang.reset_parse_cache()`/`parse_cache_stats()`
bracketing it showed 1978-1979 cache HITS against only 646-648 real
parses for the run -- i.e. `_cov006`'s ~2000-call `parse_file` pattern
T-0410 originally flagged is real in call COUNT, but T-0414's
content-hash memo (already landed) already absorbs nearly all of it into
cache hits, matching the audit's own "0s if already memo'd" estimate for
this row. Same isolated-call-slower-than-in-context anomaly as Finding 5
was also observed here (isolated wall time ~56-60s vs the 5.04s
`gate-summary` bracket for the same gate in a real `--only gates-fast`
run) -- not root-caused, out of this ticket's scope (T-0949 owns
root-causing that isolated-vs-in-context discrepancy class), noted here
only so a future pass does not re-discover it as new.

**Row 2 (`test` gate, 13.68s) and Finding 4 (sys/secrets/pii_structural
shared walk) -- explicitly NOT attempted here.** `test` gate's isolated
profile is T-0949's scope (this audit's own Finding 5 root-cause);
Finding 4's cross-gate shared walk touches `pii_structural`, a
rust-candidate row this ticket (T-0929) was scoped to stay off of
(T-0930 owns rust-candidate rows), and is separately ticketed as T-0946.
`archgate`/`static`/`dead_symbols` (rust-candidate rows) were not
touched, per the same scoping instruction.
