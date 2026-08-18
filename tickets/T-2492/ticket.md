---
id: T-2492
title: audit other --json runners for the same unguarded-stdout-write class T-2486
  fixed in check
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
