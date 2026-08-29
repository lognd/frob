---
id: T-3350
title: Decompose the serve/tickets/testing/app CYCLE001 SCC (160 nodes, post-1.0.0)
state: done
kind: feature
origin: human
created: '2026-08-29'
priority: low
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__init__.py
- src/frob/nodeid.py
- src/frob/gates/__init__.py
- src/frob/tickets/_scope_coverage.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_worktree_sweep.py
- src/frob/tickets/__init__.py
- src/frob/lang/_extract.py
- src/frob/lang/__init__.py
- src/frob/check/_python.py
- src/frob/app/cycle_runner.py
- src/frob/app/worktree_runner.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/arch/__init__.py
- src/frob/arch/_python.py
- src/frob/serve/_socketd.py
- src/frob/testing/_collect_cpp.py
- docs/modules/lang.md
- tests/unit/test_nodeid.py
- tests/system/test_cli_cycle.py
- tests/test_worktree_guard.py
- tests/unit/test_rapid_sweep.py
- tests/test_ticket_leases.py
- tests/unit/test_unlanded_branch_work.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/serve/**
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/tickets/**
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/testing/**
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/app/_daemon_proxy.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/__init__.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/nodeid.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/__init__.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_scope_coverage.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_worktree_sweep.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/lang/_extract.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/lang/__init__.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/check/_python.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/cycle_runner.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/arch/__init__.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/arch/_python.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/testing/_collect_cpp.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/lang.md
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_nodeid.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/system/test_cli_cycle.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_worktree_guard.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: T-3350 turned out to be a real, up-to-date CYCLE001 fix (measurement-artifact
    detector bug plus 4/6 real small cycles collapsed), not the stale 160-node serve/tickets/testing/app
    epic this ticket previously described -- narrowing scope to the exact files actually
    touched; the two remaining small cycles (graph<->lock, telemetry) need an owner
    design pick, see done report.
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_ticket_leases.py
  reason: ty caught two more test files still importing sweep_worktrees/_list_agent_worktrees
    through the removed frob.tickets._leases re-export
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: ty caught two more test files still importing sweep_worktrees/_list_agent_worktrees
    through the removed frob.tickets._leases re-export
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'COV001: doc anchor for the extracted frob.nodeid.symref_to_nodeid'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'COV001: doc anchor for the extracted frob.nodeid.symref_to_nodeid'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/system/test_cli_cycle.py::test_toplevel_two_module_cycle_fires
- tests/system/test_cli_cycle.py::test_deferred_only_cycle_does_not_fire
- tests/unit/test_nodeid.py::test_plain_dotted_qualname_becomes_double_colon
- tests/unit/test_nodeid.py::test_bracketed_case_suffix_dots_pass_through_unchanged
- tests/unit/test_nodeid.py::test_no_qualname_separator_is_a_noop_on_the_path_side
designated_repro_test: tests/system/test_cli_cycle.py::test_deferred_only_cycle_does_not_fire
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a07433b7215188fd5acd6985054978ec304c6eb6
---
Post-1.0.0 epic: decompose the serve/tickets/testing/app CYCLE001 SCC
(160 nodes). Owner decision on T-2667 (2026-08-29) was accounting-now,
decomposition-later: this epic carries the corrected edge analysis
forward so the real work is not lost.

Carried forward from T-2667 (measured, not guessed): after candidate 2
(stats -> tickets) landed, the SCC did NOT shrink -- still 160 nodes,
still closed, now entirely by edges that never route through frob.stats.
At least five edges close it:

1. candidate 1 -- serve/_tools.py:24, top-level
   `from frob.tickets import doable, load_queue`.
2. candidate 3 -- tickets/_land.py, function-local
   `from frob.testing._models import CollectedTests`.
3. candidate 4 -- testing/_coverage_wait.py:163, function-local
   `from frob.app._daemon_proxy import release_daemon_lease,
   try_daemon_lease`.
4. candidate 5 -- app/_daemon_proxy.py, several function-local
   `from frob.serve import ...`.
5. a sixth edge T-2363's original analysis missed -- serve/_tools.py:606,
   a second, independent function-local
   `from frob.testing import SelectConfig, load_runners, run_selected,
   select_tests`.

TWO DIFFERENT PROBLEMS IN ONE TICKET -- pick which this epic is fixing
before starting, do not conflate them:

- A genuine IMPORT-TIME risk (can actually deadlock/cycle at import):
  exactly ONE of the five edges is a top-level import --
  serve/_tools.py:24 (candidate 1). This is the only edge that can bite
  at module-load time.
- The DEPENDENCY-GRAPH SCC as CYCLE001's static analysis measures it:
  all five edges close it, but four of them (tickets/_land.py,
  testing/_coverage_wait.py:163, app/_daemon_proxy.py, and
  serve/_tools.py:606) are function-local imports and cannot deadlock an
  import by construction -- they only make CYCLE001's graph-level finding
  fire.

Fixing only candidate 1 removes the sole real import-time risk but will
NOT collapse the 160-node SCC as CYCLE001 measures it (the other four
edges still close the cycle). Fixing all five is the only way to make
CYCLE001 itself go green. State up front, before work starts, which of
these two outcomes this epic is targeting.

candidate 4/app/_daemon_proxy.py's honest fix (per repo owner, carried
from T-2583) is extracting shared daemon-protocol primitives into a
neutral module both app and serve import, mirroring T-2358's
deploy/_generate_common.py extraction -- not inversion.

Evaluate the remaining edges AS A SET, not one at a time, and re-measure
`frob cycle` / `frob check --only cycle` after any candidate pick --
T-2363's own second-edge-missed history on this exact package pair is
precedent that "the smallest-looking edge is sufficient" cannot be
assumed.

Not a release blocker: the cycle is waived (well, tracked as debt as of
T-2667's close) and was not among the 213 CI-hard release-blocking
errors. Scheduled for post-1.0.0.