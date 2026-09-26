---
id: T-6587
title: 'frob coverage --full: subprocess-coverage .pth hook raises in spawned children
  and fails subprocess-honesty tests that pass under plain pytest'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/testing/_coverage_refresh.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 902
  new_length: 1008
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26), filed there as T-draft-e2d207bc;
the cause is frob-side. `frob coverage --full --fail-on-degraded` writes
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->`.frob/coverage-subprocess.rc` (`_write_coverage_subprocess_rc`,
concurrency=multiprocessing) and child processes spawned by the tests
auto-start coverage through the site .pth hook; that hook throws in the
child, pollutes stderr and fails 3 crunk subprocess-honesty tests that are
green under plain pytest.

Reproduce in a fixture: a test that spawns `sys.executable -c "print(1)"`
and asserts empty stderr; green under pytest, red under `frob coverage
--full`. Fix so the child either starts coverage cleanly (rc reachable and
valid from the child's cwd, COVERAGE_PROCESS_START pointing at an absolute
path) or does not start it at all when the rc is not applicable; never a
traceback on the child's stderr. Designated repro: the fixture test above.
