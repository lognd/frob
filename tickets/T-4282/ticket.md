---
id: T-4282
title: graph cache write lock blocks readers for a build's duration; name the holding
  process on CacheLocked
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- src/frob/graph/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: T-4282's new tests exercise the lock-holder-naming and periodic-commit fixes;
    adding coverage in these existing test files is part of doing this ticket correctly
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: T-4282's new tests exercise the lock-holder-naming and periodic-commit fixes;
    adding coverage in these existing test files is part of doing this ticket correctly
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/test_graph.py
  reason: 'reverting: adding these huge shared test files to scope pulled in their
    pre-existing unrelated private-helper cross-references (SCOPE002 under-capture),
    a repo-wide cascade unrelated to this ticket''s actual fix'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/unit/test_graph_cache.py
  reason: 'reverting: adding these huge shared test files to scope pulled in their
    pre-existing unrelated private-helper cross-references (SCOPE002 under-capture),
    a repo-wide cascade unrelated to this ticket''s actual fix'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given a running serve daemon mid-build, when another process opens the graph
    cache for a read or its own build, then it succeeds rather than timing out
  evidence: []
- text: given a graph build that cannot take the cache lock, when it reports CacheLocked,
    then the message names the PID (and where determinable, the command) of the process
    actually holding the lock
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4258 (serve daemon 19-hour lock-starvation incident) because both fixes require touching src/frob/graph/cache.py, outside T-4258's own src/frob/serve/_daemon.py + src/frob/serve/_warm.py scope. T-4258 itself only delivered its 4th, self-contained obligation (idle self-termination); this ticket carries the other two. IMPORTANT PRIOR ART, read before touching journal_mode: T-3644 deliberately RETIRED WAL journal mode for TRUNCATE after WAL's -shm mmap caused SIGBUS crashes (see cache.py's own T-3644 comments at multiple points, e.g. around 'Round 5 of the cache lock-contention saga'). Do not re-enable WAL to get concurrent readers without addressing that SIGBUS class first, or re-check whether it is still applicable. Investigated: build_graph's own conn.close() runs unconditionally in a finally block, and connect()/connect_readonly() open a fresh connection each call with no pooling -- no leak was found in _daemon.py/_warm.py's current code reachable in a genuinely idle repo (no main-HEAD movement). The plausible real mechanism, given this repo's own busy multi-agent fleet-root usage: _poll_post_land re-verifies IMMEDIATELY and synchronously on every single main-HEAD movement (no debounce, unlike the sibling CoalescingWorker job), so in a root where lands happen every few minutes, the daemon becomes a near-constant additional writer contending with every other frob invocation's own build_graph call on the SAME shared .frob/cache.db -- worth measuring directly (a busy fleet root's cache.db lock-wait histogram) before deciding between (a) a debounce/coalesce on the daemon's own re-verify trigger -- NOTE this would require changing the bound, synchronous, immediate-refresh contract tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict currently pins, so any debounce needs a signature/behavior change coordinated with that test, not a silent violation of it -- or (b) shortening how long build_graph's own write transaction stays open (e.g. periodic intermediate commits during _ingest_source_files instead of one commit at the very end) which needs no daemon-side change at all.