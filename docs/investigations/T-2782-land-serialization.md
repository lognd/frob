# T-2782: is landing's ~300s critical section cheapenable?

Measured in a real, natives-built ticket worktree merged onto main tip
at measurement time (a gitignored path under `.claude/worktrees/`, not
itself a tracked reference), via direct profiling of
`frob check --ticket` (the exact spawn `_land_locked` makes,
`_shared_check_spawn_fn` in `src/frob/app/ticket_runner/_verify.py`) and
by mining this repo's own `git log` for real inter-land timing --
`PYTHONFAULTHANDLER`/estimation was not needed because the check spawn
already reports authoritative per-stage wall time via `frob check --json`
(`gate-summary`'s own `[stage=Ns, ...]` breakdown), which is a more
precise instrument than a fixed-offset stack sample would have been.

## Answer 1: what fraction of the ~300s is `check_gates()` vs merge/finalize/squash?

Cold run (fresh worktree, no prior cache entry for this tree):

```
$ time uv run frob check --ticket T-2782 --json
real 274.56s   user 261.49s   sys 71.51s
```

Consecutive re-run against the byte-identical tree:

```
$ time uv run frob check --ticket T-2782 --json
real 97.21s
gate-summary: "[REPLAY age=65.3s, unchanged tree]  ... [same per-stage numbers]"
```

The second run is not a cheaper re-execution -- `gate-summary`'s own
message says `REPLAY`: the whole prior `CheckResult` is served verbatim
from a whole-tree digest cache, not recomputed. The 97s is the cost of
detecting "unchanged" and replaying, not a discount on any individual
gate. **This matters directly for Answer 2 below: the replay path
requires a BYTE-IDENTICAL tree, and a freshly-merged land tree is never
byte-identical to anything previously checked, so a real land can
structurally never hit it** -- corroborating, with a fresh number, the
`_shared_check_spawn_fn` docstring's existing claim ("this spawn NEVER
gets that benefit in practice... the cache structurally near-always
misses at land time").

So the cold number, 274.56s, is the realistic per-land cost of
`check_gates()` alone. This repo's own prior investigation (T-1344/
T-2053, recorded in `_shared_check_spawn_fn`'s docstring,
`src/frob/app/ticket_runner/_verify.py`) measured this spawn at "~209s
of a ~95-320s land" from real land instrumentation -- my fresh number
(274.56s) falls inside that same historical range on a repo that has
grown since. Merge/finalize/squash (`_land_merge_stage`,
`_land_finalize_and_close`, `_land_squash_apply`) are plain git
operations (checkout, merge, commit, one `git reset --soft` + `git
commit` for the squash) -- these run in low single-digit seconds on this
repo's tree size; I did not additionally instrument them because the
existing land timing already brackets `check_gates()` at 65-90% of the
total, and my own cold-run number sits at the observed ceiling of that
range for a repo this size. There is also a SECOND, uncounted cost:
`_land_gate_claims_fn` (T-1410, `_land_cmd.py`) spawns its own
comparably-sized `frob check --only gates` against `worktree` for the
acceptance-criteria gate-claim check -- outside `_land_locked`'s own
`check_gates()` call but still inside the lock. The true critical-section
total is therefore check-dominated by an even wider margin than the
~209/300 figure states on its own.

**Finding: `check_gates()` (plus its uncounted `_land_gate_claims_fn`
sibling) is the large majority of the ~300s critical section. Merge/
finalize/squash is not the bottleneck.**

## Answer 2: how much of that is genuinely post-merge-dependent?

Breaking down the cold run's own `gate-summary` stage timings (unit:
seconds, sorted descending), the check spawn's cost is concentrated in a
small number of families:

| stage | s | family |
|---|---|---|
| sys | 69.78 | capability/effect flow model (`frob.strata`) |
| perf | 59.63 | performance-pattern analysis |
| archgate | 45.44 | architecture (coupling, god-class, long-function) |
| dead_symbols | 34.08 | cross-file reachability |
| coverage | 32.70 | doc/test coverage graph |
| tickets | 25.46 | ledger-wide scan (T-2557's own family, among others) |
| clones | 18.15 | duplicate-code detection |
| refs | 18.02 | cross-file reference resolution |
| pii_structural | 16.00 | structural PII scan |
| (44 more stages) | ~28 | assorted, each under 10s |

These top 9 families alone account for ~319s of stage time (stages
overlap across worker processes, so their sum exceeds the 274.56s wall
clock -- consistent with the checker parallelizing independent gate
families rather than running them serially). The dominant cost centers
-- sys, perf, archgate, dead_symbols, coverage, clones, refs -- are, by
construction, **whole-program / cross-file analyses**: call graphs,
capability-flow models, coupling metrics, and reachability all require
correctness claims that span every file, not just the ones a given
ticket's diff touched. Directly testing the fast, genuinely-per-file
tools that a leaner "diff-scoped" scheme might hope to skip straight to
confirms they are cheap on their own and were never the bottleneck:

```
ruff check .   -> 0.18s
ty check .     -> 4.90s
frob dup src/frob -> 6.37s
```

None of the actual cost sits in the fast, trivially-cacheable linter
layer. It sits in the whole-program graph analyses. This is the key
finding for Answer 2: **a change that only touches file X can change
what `dead_symbols`/`archgate`/`sys` conclude about files Y and Z that
never changed** (a new caller makes a previously-dead symbol live; a new
edge changes a coupling metric; a new capability flow changes an
effects-reachability verdict elsewhere). This is exactly what
`_shared_check_spawn_fn`'s own docstring already recorded as the reason
the T-1346 per-file digest cache "structurally near-always misses at
land time": the cache is real and working, but the properties it would
need to reuse are not decomposable by file in the way a delta-scoped
revalidation needs.

**Finding: the large majority of `check_gates()`'s cost (the sys/perf/
archgate/dead_symbols/coverage/clones/refs cluster, ~87% of stage time)
is genuinely post-merge-dependent in the strong sense -- not merely
"nobody has cached it yet" but "the correct answer for an unrelated file
can change because of this merge," which a diff-scoped revalidation
cannot soundly skip.**

## Answer 3: how often does main move between consecutive lands, and what would delta-revalidation cost?

Mined real land commits from this repo's own `git log` (24h window,
`git log --format="%ct %s" | grep "land T-"`):

- 67 lands in 24h; 66 inter-land gaps.
- Full-day distribution (includes idle overnight hours): min 43s, p25
  428s, median 638s, p75 1003s, max 26435s (mean pulled up by long idle
  gaps).
- The **busiest real 30-minute window** in that same log (6 lands,
  matching the coordinator's own observed "6 lands/30min" ceiling
  exactly) has gaps of **432s, 280s, 495s, 204s, 335s** between
  consecutive lands -- every single gap in the actually-contended window
  is the same order of magnitude as one land's own ~300s critical
  section, consistent with full serialization and no overlap (which is
  exactly what the lock enforces today).

Under the real contention this ticket is about (not the 24h average,
which includes idle time), **main moves between essentially every
consecutive land** -- the gaps are not large multiples of the land
duration, they are comparable to it. So an optimistic verify-outside-
the-lock scheme would find its recorded main tip stale on nearly every
attempt under exactly the load this ticket is trying to help, not as a
rare edge case.

Combined with Answer 2, the revalidation-cost question has an answer
that makes the "how expensive is revalidating just the delta" question
moot: **there is no cheap delta-revalidation available**, because the
dominant cost (~87% of stage time) sits in whole-program analyses whose
correct output for the CURRENT delta is not derivable from "what changed
between the recorded tip and the new tip" without re-running the same
whole-program computation. Revalidation after a main-move would cost
approximately the same ~270s the original optimistic verify already
cost, not a cheap delta.

## Conclusion

All three measurements point the same direction:

1. `check_gates()` (274.56s cold, corroborating the existing ~209/300s
   land-instrumented figure) dominates the critical section; merge/
   finalize/squash is not the bottleneck.
2. ~87% of that cost is in whole-program graph analyses that are
   genuinely post-merge-dependent -- not merely uncached, but incapable
   of being soundly scoped to a diff.
3. Under the real contention this ticket describes, main moves between
   essentially every consecutive land, so an optimistic scheme would be
   invalidated on nearly every attempt, and (per #2) the revalidation it
   would then need to run is not materially cheaper than the original
   check -- the exact "serial-plus-wasted-work, strictly worse than
   today" degenerate case the ticket's own text warned against, measured
   here as the LIKELY case, not a tail risk.

**This cannot be made cheap by moving verification outside the lock.**
Optimistic concurrency does not raise the ceiling; it adds a
near-certain-to-fail speculative attempt in front of the same serialized
work. Per the ticket's own stated acceptance of this outcome, T-2782
should be CLOSED with this finding recorded, not force-fit into an
implementation. The real lever is the cost of `frob check` itself,
specifically the whole-program families (`sys`, `perf`, `archgate`,
`dead_symbols`, `coverage`) that dominate its wall time -- a different,
already partially-scoped problem (`_shared_check_spawn_fn`'s docstring
already names two candidate directions: a digest cache extended to the
lint/static layer, which my measurement shows is NOT where the cost is
and would not move this number; and threading the land's own diff into
an `--only <affected families>` selection, which Answer 2 shows would
only safely narrow the ~13% of stage time that is NOT one of the
whole-program families -- a real but modest win, not a ceiling-raiser).

## What was NOT done

Per the ticket's own framing as a measurement, not a patch: no code
changes were made outside `docs/investigations/`. No optimistic-locking
prototype was built (the measurements above make its expected value
negative before writing any code). The two `_shared_check_spawn_fn`
docstring's own candidate cost reductions for `frob check` itself were
not implemented here -- they are a different ticket's scope.
