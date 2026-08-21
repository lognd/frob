## Done report

Measured directly rather than estimated, per the ticket's own demand.

(1) check_gates() vs merge/finalize/squash: cold `frob check --ticket`
run in the worktree measured 274.56s wall (user 261.49s, sys 71.51s),
matching this repo's own prior land-instrumented figure (T-1344/T-2053,
recorded in _shared_check_spawn_fn's docstring: "~209s of a ~95-320s
land"). Merge/finalize/squash are plain git operations (checkout, merge,
one squash commit) on a repo this size and were not the bottleneck in
either the historical or the fresh measurement. There is also a second,
previously-uncounted cost inside the lock: _land_gate_claims_fn (T-1410)
spawns its own comparably-sized `frob check --only gates` against
worktree for the acceptance-criteria gate-claim check.

(2) Post-merge dependence: broke down the cold run's own gate-summary
per-stage timings. The dominant cost sits in sys (69.78s), perf
(59.63s), archgate (45.44s), dead_symbols (34.08s), coverage (32.70s),
tickets (25.46s), clones (18.15s), refs (18.02s), pii_structural
(16.00s) -- ~319s of stage time (stages overlap across worker
processes, hence exceeding the 274.56s wall clock), roughly 87% of the
total. Directly measured the fast, genuinely per-file tools a
diff-scoped scheme might hope to lean on instead: ruff check (0.18s), ty
check (4.90s), frob dup (6.37s) -- none of the cost is there. The
dominant families are whole-program/cross-file analyses (call graphs,
capability-flow models, coupling, reachability) whose correct output
for an untouched file can change because of a merge elsewhere in the
tree -- not merely uncached, but not decomposable by file the way a
diff-scoped revalidation needs. Confirmed the existing T-1346 digest
cache's own failure mode directly: a second run against a
byte-identical tree returned in 97.21s, but gate-summary's own message
says "[REPLAY age=65.3s, unchanged tree]" -- the WHOLE prior result is
replayed verbatim, not recomputed per-gate, and this replay path
requires byte-identical trees, which a freshly-merged land tree never
is.

(3) Main-move frequency: mined this repo's own git log for real land
commits (67 in 24h). Full-day gap distribution is misleading (idle
overnight hours pull the mean up to 1292s); the busiest real 30-minute
window in the same log had exactly 6 lands (matching the ticket's own
"6 lands/30min" observation) with inter-land gaps of 432s, 280s, 495s,
204s, 335s -- every gap in the actually-contended window is the same
order of magnitude as one land's own ~300s critical section. Under real
sustained load, main moves between essentially every consecutive land,
not as a tail case.

Conclusion: all three measurements point the same direction. check_gates()
dominates the critical section (matches historical figure); ~87% of its
cost is genuinely post-merge-dependent in the strong sense (whole-program
analyses, not merely uncached); and under real contention main moves
between nearly every consecutive land, so an optimistic verify-outside-
the-lock scheme would be invalidated almost every time and would then
need to re-run the same expensive whole-program analyses again --
degenerating to serial-plus-wasted-work, the exact failure mode the
ticket's own text warned against, measured here as the likely case, not
an edge case.

This cannot be made cheap by moving verification outside the lock.
Recommending CLOSE per the ticket's own stated legitimate outcome, with
the finding recorded in docs/investigations/T-2782-land-serialization.md.
The real lever is the cost of frob check itself (the sys/perf/archgate/
dead_symbols/coverage cluster), a separate, already partially-scoped
problem per _shared_check_spawn_fn's own docstring -- not this ticket's
scope to implement.

No code was changed outside docs/investigations/. No optimistic-locking
prototype was built: the measurements make its expected value negative
before writing any code, per the ticket's own instruction not to
manufacture a redesign to look productive.

### Changed
```
 docs/investigations/T-2782-land-serialization.md | 200 +++++++++++++++++++++++
 rapid-debt.jsonl                                 |   1 +
 tickets/T-2782/done-report.md                    |  83 ++++++++++
 tickets/T-2782/ticket.md                         |  24 ++-
 4 files changed, 305 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:wc -l docs/investigations/T-2782-land-serialization.md exit=0 sha256=1f01d1b4b0cc` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 19 error(s), 834 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2782, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
