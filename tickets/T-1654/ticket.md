---
id: T-1654
title: Audit remaining real-repo build_graph tests for T-1433/T-1635 xdist self-scan
  contention
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
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