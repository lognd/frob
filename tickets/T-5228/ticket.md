---
id: T-5228
title: 'macOS CI aborts at 2400s again (exit 134): different from T-4641''s tick008
  hang, no per-test timeout preceding it'
state: in-progress
kind: bug
origin: human
created: '2026-09-21'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: added the crash-free stall predicate's own unit test in the same file its
    siblings live in
  actor: logan
  at: '2026-09-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5228
branch: t-5228
---
Found while burning down fresh CI run 35654510898 (dev tip a85fb35e12). The macos-latest job's "Test (macos, timed with stack-dump-on-hang)" step aborted with exit 134 (SIGABRT) after exceeding its 2400s budget (T-3250's own watchdog: "macOS Test step exceeded 2400s with no completion") -- this is a DIFFERENT occurrence than T-4641's already-fixed tick008/_FENCE_RE hang: this run's progress bar reached 87% (vs ~77% in the earlier, now-fixed T-4641 incident) and there is no per-test SUITE-RESULT-FAILED "exceeded Xs timeout" line anywhere in the log immediately before the abort -- the xdist master thread is simply idle in dsession.loop_once waiting on a worker queue message that never arrives, same generic shape as before but with no single identifiable culprit test this time.

Two hypotheses, need actual investigation (not guessed at here):
(a) A genuine NEW hang in some other test near the 85-90% collection mark (progress dots do not name tests under -q, so the exact test is unknown from the log alone -- would need a local repro with -v or a stall watchdog that prints per-test names).
(b) General throughput exhaustion: the full suite now simply does not fit in the 2400s macOS budget under current repo size/fleet load (consistent with the already-filed T-5153 "frob check: the sys stage takes 1268s of a 1900s root check" perf finding, and this session's OWN direct measurement: `frob check --only gates` did not complete within a 580s budget under this session's fleet contention either) -- if so this is a budget/perf ticket, not a hang-bug ticket, and the fix is either raising T-3250's 2400s macOS ceiling with a measured justification, or reducing macOS suite wall time (splitting the job, more xdist workers, etc.), not chasing a phantom deadlock.

Reproduce locally on macOS (this session has no macOS runner available) with PYTHONFAULTHANDLER and a stall watchdog that prints the in-flight test name per worker (tests/conftest.py already has `_run_stall_watchdog`, T-3250's own mechanism -- extend it to log the currently-running node id per xdist worker if it does not already) BEFORE deciding which of (a)/(b) applies. Cross-reference already-filed T-3213 (macOS CI SYS107/SYS003 selfconform triage) and T-3274 (extend T-3192 hang-guard positive control to macOS/Windows) -- this may be the same underlying macOS-specific slowness those tickets already describe, not a new class.
