## Done report

MEASURE-FIRST, per plan. Fresh `frob check` stage timing on this checkout
showed the ticket's grounding numbers (archgate=153.6s, sys=145.3s) already
stale: both are 0.00s/~0.9s today, mooted by T-0423's `@memoize_per_run` on
`build_graph`/`analyze_project` (landed after the original perf audit but
before this ticket started -- confirmed via T-0418, closed this session as
verify-first/no-code-change). Re-profiled `frob check` with the giants gone
and found the new dominators: `coverage` (36-45s) and `refs` (8-11s), every
other stage <5s.

Isolated `coverage_gate` under cProfile (natives built, real repo) and found
a fresh instance of the audit's own H4 class ("no shared single-parse
pass"): COV006's rescue helpers (`_cov006_third_file_reachable`,
`_cov006_public_wrapper_reachable`) call `frob.lang.parse_file` ~2000+
times per run, many repeats on the same path across different candidate
edges. `_parse` (the raw tree-sitter parse) already has its own content-hash
cache, but `extract()` (the symbol/comment AST walk) was never cached, so a
repeat `parse_file` call re-ran the full walk even on a `_parse` cache hit --
measured ~151s of a ~156s isolated `coverage_gate` profile inside
`_walk_python`/`_common.walk`.

Landed fix: `@memoize_per_run` on `frob.lang.parse_file`, applied via a
first-call-deferred wrapper (`_parse_file_uncached` + public `parse_file`)
rather than a module-level decorator, to avoid a real `frob.lang`/
`frob.check` circular import (`frob.check.__init__` imports `frob.lang` at
module scope; a top-level `from frob.check._memo import memoize_per_run` in
`frob.lang` fails the moment anything imports `frob.lang` before
`frob.check` finishes, e.g. `frob.arch` -> `frob.lang` -- reproduced and
confirmed before choosing the lazy-wrap design).

Measured impact: isolated `coverage_gate` profile 155.8s -> 15.9s (~10x);
real `frob check`'s `coverage` stage timing 36-45s -> 3.3-4.7s across
several repeat runs. Since `parse_file` is a shared chokepoint, this
generalizes to any other caller hitting the same path repeatedly in one
run without further call-site changes -- consistent with T-0423's own
design intent.

Also landed (cheap, in scope, verified zero-risk): finding M6 from
`docs/audits/perf.md` -- added `.hypothesis` and `.serena` to
`frob.excludes.BUILTIN_SKIP_DIRS`. Neither has a tree-sitter grammar, but
every rglob-based stage was walking/stat'ing/opening every entry inside
them (measured in the original audit: 1298 `.hypothesis/constants` + 44
`.hypothesis/examples` + `.serena/cache` files).

`docs/audits/perf.md` updated with a dated 2026-07-21 re-measurement
section: H1/H2 marked RESOLVED (T-0423), the new coverage_gate finding and
fix documented, M6 marked landed, and two structural follow-ups not filed
rather than solved in this ticket:
- T-draft-9f90cc43 (never refiled): H3 (thread pool vs process pool for CPU-bound gates) --
  lower urgency now that the two original giants are gone, but the
  architecture gap is unchanged and will resurface with any new heavy
  thread-pooled gate.
- T-draft-bafbce1c (never refiled): re-verify H4's other cited multipliers (vet's
  `raw_tree`-based capability scan bypasses the new `parse_file` memo
  entirely; H5's selfconform double-scan) and profile the new `refs` stage
  dominator (~8-11s, never profiled by the original audit) -- explicitly
  NOT assumed fixed without a fresh profile.

REL001: public API behavior of `frob.lang.parse_file` changed (memoized
within an active `run_memo_scope`); bumped `pyproject.toml` 0.68.0 ->
0.69.0, added a CHANGELOG entry, ran `frob release stamp`.

No frob-core/strata-core (Rust) changes made this pass -- the measured
hotpath was pure-Python (`extract()`'s AST walk), not a Rust-lowering
candidate; a native rewrite was not attempted since a Python-level cache
fix already closed 10x of the measured gap at far lower risk.

### Changed
```
 tickets.md | 45 +++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 43 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)
