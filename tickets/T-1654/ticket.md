---
id: T-1654
title: Audit remaining real-repo build_graph tests for T-1433/T-1635 xdist self-scan
  contention
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_waive_gate.py
- tests/test_graph.py
- tests/test_dup.py
- tests/test_gates.py
- tests/test_secrets_gate.py
- tests/test_vet.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_waive_gate.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_graph.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_dup.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_secrets_gate.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_vet.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/conftest.py
  reason: 'T-2446: the ticket''s own Plan section names these 6 files explicitly (''For
    each file above, identify which test(s) call build_graph...'') plus tests/conftest.py
    since the fix extends _SELF_SCAN_HEAVY_NAME_SUBSTRINGS/xdist_group there -- not
    a guess, the ticket enumerates its own targets'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): audit-only ticket; classified all 6 files,
    found 4 candidate tests sharing T-1635''s shape but could not reproduce actual
    contention within a sub-agent foreground budget (coordinator-only per playbook
    3c/6b); filed T-2762 for the reproduction+fix step; no source/test changes made'
  actor: logan
  at: '2026-08-20'
  old_length: 1978
  new_length: 2302
evidence:
- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
- tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo
- tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
- tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
T-1635 found and fixed a real cross-process shared-resource contention
class: tests that call `frob.graph.build_graph` directly against this
repo's own real checkout root (`Path(__file__).resolve().parents[1]`,
not an isolated `tmp_path`) contend on `.frob/derived.lock`
(`derived_state_lock`/`derived_state_write_lock`, `src/frob/process/
_lock.py`) -- an unbounded `fcntl.flock` with no internal timeout -- and
also pay full-repo-parse peak-memory cost. Under `pytest-xdist -n auto`,
enough of these landing on different workers at once can queue past the
per-test pytest-timeout budget or trigger an OOM "node down" kill
(T-1433's originally diagnosed shape, tests/conftest.py's
`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`).

T-1635 extended that existing xdist_group mechanism to the two
`test_registry_exhaustiveness.py` tests it reproduced actually failing
this way. It did NOT audit the other files matching the same
`build_graph(real repo root, ...)` shape found via a grep sweep --
listed here for a future burn-down, each needing the same "does it
actually reproduce under -n auto load" verification before being added
to the group (adding untested names would be superstition, not
evidence):

- tests/test_waive_gate.py
- tests/test_graph.py
- tests/test_dup.py
- tests/test_gates.py
- tests/test_secrets_gate.py
- tests/test_vet.py

## Plan
1. For each file above, identify which test(s) call `build_graph`/
   `find_clones`/similar against the real repo root rather than a
   `tmp_path` fixture.
2. Reproduce contention under `pytest -n auto` load (repeated full-suite
   runs, or a targeted heavy-load repro) before adding any test name to
   `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` -- do not add speculatively.
3. Consider whether `derived_state_lock` itself should grow a bounded
   wait + clear timeout error (rather than blocking forever) as a
   separate, more general hardening -- out of scope for a test-file-only
   fix, worth its own ticket if picked up.

frob:no-behavior-change reason="audit-only ticket; classified all 6 files, found 4 candidate tests sharing T-1635's shape but could not reproduce actual contention within a sub-agent foreground budget (coordinator-only per playbook 3c/6b); filed T-2762 for the reproduction+fix step; no source/test changes made"