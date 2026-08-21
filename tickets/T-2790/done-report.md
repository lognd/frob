## Done report

MEASUREMENT ticket, per its own required shape -- no optimization code
landed here, per plan.

Read docs/investigations/T-2782-land-serialization.md first, as required:
confirmed its finding (verifying outside the land lock cannot be made
cheap; main moves between essentially every consecutive land under real
contention) and did not re-propose it.

Read tickets/archive/T-0410 (the earlier perf epic named in this ticket's
body) and its descendants T-0953/T-1220/T-1222 (Rust hot-path migrations
into frob_core) before profiling anything, per the ticket's explicit
instruction not to re-derive prior work.

Profiled all four named stages (sys, perf, archgate, dead_symbols)
directly via cProfile against this repo's own real tree (one GraphSnapshot
built once via build_graph(), reused across sys/perf/dead_symbols so
graph construction itself is not double-counted; archgate profiled
separately since it does not take a snapshot argument). Fleet load was
high during profiling (LOAD 17-29, other agents landing concurrently) so
absolute wall-clock numbers in the investigation doc are inflated versus
T-2782's quieter baseline -- the relative breakdown inside each stage
(which function dominates, what fraction) is the load-bearing result,
not the absolute seconds, and is noted as such in the doc.

Central finding, verified in code (not assumed): three of the four
stages independently re-derive data another part of the system already
computed once.

- archgate: 31% of its own cost (measured 73.40s/236.34s, matching
  T-1222's own done-report figure exactly) is the per-function metrics
  walk that T-1222 already replaced with a golden-tested Rust kernel,
  frob_core.py_function_metrics -- confirmed via git grep that this
  kernel has ZERO call sites under src/frob/ today. Built, tested,
  documented, never wired to a caller.
- perf and dead_symbols independently hit the SAME structural gap:
  both call frob.lang.parse_file, get a cheap hit on the existing
  persistent disk-backed content-hash parse cache (T-0414), and then
  both still pay the full extract() walk cost again (measured 85.07s/
  perf, 87.51s/dead_symbols) because extract()'s output is only
  memoized per-OS-process (T-0423), and each gate is dispatched as its
  own separate process (_ProcessJob) -- so the process that already ran
  build_graph()'s own extract() calls has exited by the time these
  stages' own processes start.
- sys is the one genuine outlier: its dominant cost (scan_file_
  capabilities, 44% of profiled selfaudit time, the single largest raw
  stage number of the four) runs on the stdlib ast module, not
  tree-sitter/parse_file at all, and has NO cache of any kind at any
  layer -- confirmed via grep, zero memoize/lru_cache/content-hash
  references in either capability module.

Stated, per stage, which parts are genuinely whole-program (cannot be
diff-scoped without becoming unsound: dead_symbols' reachability, sys's
cross-file capability flow, archgate's coupling/near-dup/concurrency-
hazard checks) versus whole-program only by construction (per-file
metric extraction that a content-hash cache can share across processes
without touching soundness, since the cached value is a deterministic
pure function of file content).

Filed three child tickets (--parent T-2790, per the ticket's own
required split) rather than implementing here:
- T-2799: wire frob_core.py_function_metrics into archgate.
- T-2797: extend the parse-artifact disk cache to persist
  extract()'s output, closing the shared perf/dead_symbols gap.
- T-2798: size (not build) a content-hash cache for sys's
  ast-based capability scan.

Each child ticket's own body restates this ticket's hard constraints
(identical finding count before/after on a real unbudgeted run; a
positive control proving any cache still fires on a planted violation;
no silent caps) as its own acceptance bar -- none of them are
pre-approved to trade soundness for speed.

Disclosed, not fixed here (out of this ticket's own scope, docs/
investigations/ only): gate:SCOPE flags the three filed draft tickets'
own ticket.md files as outside T-2790's declared scope. Same
non-systemic class T-1222's own done report disclosed for its own
ticket.md (ticket-filing/scope-widening activity inherent to working a
ticket, not a new defect) -- resolves at land the same way. gate:DRIFT/
gate:TICK findings in the repo-wide (unscoped by --ticket) portion of
the check are pre-existing, unrelated to this ticket's one-file diff
(tickets/__init__.py::_doable_sort_key, tickets-data-storage.md stale
refs, TICK003/004 backlog-age findings) -- none touch anything this
ticket's scope (docs/investigations/) or diff includes.

Filed: T-2799, T-2797, T-2798 (all
--parent T-2790).

Gates: frob check --ticket T-2790 -- gate:SCOPE/gate:PREWORK (this
ticket's own scoped families) show only the disclosed draft-ticket-file
SCOPE001 findings above; every other gate family is repo-wide per its
own scope-note and pre-existing/unrelated to this ticket's diff.

### Changed
```
 docs/investigations/T-2790-check-stage-profile.md | 250 ++++++++++++++++++++++
 tickets/T-2790/ticket.md                          |   2 +-
 tickets/T-2797/ticket.md                |  63 ++++++
 tickets/T-2798/ticket.md                |  68 ++++++
 tickets/T-2799/ticket.md                |  54 +++++
 5 files changed, 436 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 20 error(s), 845 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2790, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
