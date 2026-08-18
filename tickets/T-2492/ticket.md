---
id: T-2492
title: audit other --json runners for the same unguarded-stdout-write class T-2486
  fixed in check
state: done
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/arch_runner.py
- src/frob/app/bind_runner.py
- src/frob/app/clean_runner.py
- src/frob/app/debt_runner.py
- src/frob/app/deprecated_runner.py
- src/frob/app/docs_runner.py
- src/frob/app/doctor_runner.py
- src/frob/app/dup_runner.py
- src/frob/app/exports_runner.py
- src/frob/app/fleet_runner.py
- src/frob/app/fmt_runner.py
- src/frob/app/gitlog_runner.py
- src/frob/app/graph_runner.py
- src/frob/app/map_runner.py
- src/frob/app/mutate_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/parse_runner.py
- src/frob/app/perf_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/registry_runner.py
- src/frob/app/stats_runner.py
- src/frob/app/test_runner.py
- src/frob/app/verify_runner.py
- src/frob/app/vet_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/check_runner.py
- src/frob/app/_json_guard.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/*.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/arch_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/bind_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/clean_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/debt_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/deprecated_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/dup_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/exports_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/fleet_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/fmt_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/gitlog_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/graph_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/map_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/mutate_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/parse_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/perf_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/registry_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/stats_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/test_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/vet_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_json_guard.py
  reason: narrow umbrella scope to the 26 --json runner files T-2486 identified plus
    a possible shared-guard module home; excluded ticket_runner/_new.py and _closeout.py
    held by T-2455 lease
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_json_guard_t2492.py
  reason: new regression test file for the --json stdout-guard audit findings
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: re-point a stale WIRE001 follow_up citation that blocked closing this ticket
    (LiveTrackerCited)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestFmtRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestCleanRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestMapRunnerJsonGuard::test_daemon_disabled_log_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestDocsRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard::test_daemon_disabled_log_does_not_reach_stdout
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2486 built a structural boundary guard (_guard_json_stdout_writes /
_StderrRedirectStdout in src/frob/app/check_runner.py) that redirects
any stray stdout write to stderr for the duration of a --json frob
check run, closing the class of leak T-2484 hand-fixed one instance of
(a misleveled log call in frob.__main__ corrupting frob check --json
under fleet load).

T-2486's own audit (scoped to check_runner.py only, per its ticket
scope) enumerated every --json-bearing CLI flag repo-wide via
src/frob/_cli_parsers/: 27 distinct dest= names (arch_json, bind_json,
check_json, clean_json, debt_json, deprecated_json, docs_json,
doctor_json, dup_json, exports_json, fleet_json, fmt_json, gitlog_json,
graph_json, map_json, mutate_json, outline_json, parse_json, perf_json,
profile_json, registry_json, stats_json, test_json, ticket_json,
verify_json, vet_json, xref_json), across 53 add_argument call sites
(some dest names are shared by several subcommands under the same
parent, e.g. ticket_json across many "frob ticket" subcommands,
verify_json across several "frob verify" subcommands). check_json
(frob check) is the only one T-2486 protected.

This ticket: audit each OTHER --json-mode runner for the same
unguarded-write class -- does anything in that runner's call stack
(its own module, or anything it calls into) write to stdout via a
misleveled log call, a bare print, or any other path NOT gated behind
that runner's own --json flag, the way T-2473's advisory leaked into
frob check --json before T-2484? For any found, either apply the same
_guard_json_stdout_writes pattern (may need lifting to a shared home
outside check_runner.py, since these runners are NOT scoped to that
file, e.g. frob.render or a new small module) or file per-runner
fixes. Report the count even if zero for a given runner. Do NOT weaken
any existing --json output correctness to do this -- must-still-emit
(byte-identical legitimate payload) and must-still-inform (diagnostics
still reach stderr, never silently swallowed) apply here exactly as
they did for T-2486.