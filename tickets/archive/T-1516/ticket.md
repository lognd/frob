---
id: T-1516
title: 'coverage: frob-native auto-refresh command replacing Makefile orchestration'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/**
- src/frob/check/__init__.py
- Makefile
- docs/modules/gates.md
- src/frob/gates/_coverage.py
- tests/test_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_coverage.py
  reason: 'T-1517 (closed) touched these same three files; T-1516''s own diff

    still carries follow-on interface-sync/coverage-cache wiring in

    design/frob.strata, src/frob/gates/_coverage.py, and

    tests/test_coverage.py from the same worktree session (T-1517''s

    own scope is done and cannot be reopened) -- widening T-1516''s

    scope to cover the file-level touches this worktree''s later commits

    made, since T-1516 is the open ticket landing them.

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_coverage.py
  reason: 'T-1517 (closed) touched these same three files; T-1516''s own diff

    still carries follow-on interface-sync/coverage-cache wiring in

    design/frob.strata, src/frob/gates/_coverage.py, and

    tests/test_coverage.py from the same worktree session (T-1517''s

    own scope is done and cannot be reopened) -- widening T-1516''s

    scope to cover the file-level touches this worktree''s later commits

    made, since T-1516 is the open ticket landing them.

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: docs/modules/testing.md
  reason: 'AFFECT001 requires the affects()-closure doc for the new coverage-cache/

    coverage-refresh public API (docs/modules/testing.md#public-api) to be

    updated in the same diff as the code -- widening T-1516''s scope to cover

    that doc file.

    '
  actor: logan
  at: '2026-08-04'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _coverage_wait.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1184
  new_length: 2674
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
- tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps
- tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err
- tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1205 acceptance[0], [3], [4]: a frob-native command (frob coverage or
frob test --coverage) that performs the whole orchestration -- subprocess
rc generation, pytest invocation restricted to the touched set, combine,
xml, stamp -- in Python with no Makefile/shell dependency, cross-platform
(Linux/macOS/Windows); and wiring so that any frob command whose gates
need coverage data runs this refresh automatically when the freshness
contract (TEST011/TEST017) says stale, with no user-invoked refresh verb
and nothing cached re-run. Today this logic lives in Makefile's
coverage/coverage-fast targets (shell, T-1397) and nothing in
src/frob/check or src/frob/gates triggers a refresh automatically --
frob check reads whatever coverage.xml/frob-coverage.lock.json happen
to be on disk and reports staleness (TEST011/TEST017) rather than fixing
it. Sequenced AFTER the per-file content-hash caching ticket (this
ticket's sibling, filed same session) since the native orchestrator
needs that caching layer to avoid re-running everything on every gated
command. Re-filed after the original T-1205 session's draft ids
(T-1487/T-1488) were lost to an unrelated ledger renumber.
</content>

T-4718 sweep (condensed from src/frob/testing/_coverage_wait.py:394-423,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-1516: `command=None` (the default) auto-wires the refresh through the
# in-process native path -- see the T-1516 note above `_run_and_settle_
# shared` for what that means and why.
#
# T-1095: before falling through to the per-worktree lock/run below, this
# checks the CROSS-worktree layer first -- `tree_digest` computed from the
# same snapshot, a shared cache keyed by that digest under
# `shared_state_dir`. A cache hit (another worktree with byte-for-byte
# identical tracked source already settled this digest) adopts that
# result (`_adopt_shared_result`) and returns immediately, with ZERO
# subprocess spawned in THIS worktree -- acceptance [0]. A cache miss
# acquires the shared per-digest lock (serializing every worktree sharing
# this digest onto one real run, re-checking the cache once more after
# acquiring it in case a racing worktree just finished), runs the refresh
# exactly as before, and records the settled result for every other
# worktree sharing this digest to find. Two worktrees whose tracked source
# DIFFERS resolve to different digests -- different lock paths, different
# cache entries -- so they never contend or share a result with each
# other at all (acceptance [1]).
#
# T-1126: the OUTER lock is `_worktree_lock` (daemon lease when reachable,
# else `_coverage_lock`).