---
id: T-3655
title: hotgraph sampler overhead flake exceeds even widened CI tolerance
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/perf/test_hotgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: perf flake evidence cannot be deterministically reproduced'
  actor: logan
  at: '2026-09-01'
  old_length: 1457
  new_length: 1959
evidence:
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33513484322 ubuntu:
  tests/unit/perf/test_hotgraph.py::TestStackSampler::
  test_overhead_under_five_percent
  E  sampler overhead 0.5382 exceeded the 0.35 budget (worker_id=gw3
     baseline=0.1845s cpu sampled=0.2838s cpu)

A CPU-relative perf assertion under xdist load on a shared CI runner --
classic noisy-neighbor flake (the test's own docstring already
acknowledges noise). Fix per repo precedent for perf tests: pin it to a
serial xdist_group (like frob_self_scan_heavy) OR raise/calibrate the CI
tolerance with a comment citing this run's measured 0.54 under gw3
contention -- prefer the serial group (keeps the assertion strong).
Scope: tests/unit/perf/test_hotgraph.py.

Investigation note for whoever works this: the test's OWN docstring
already documents that a serial/xdist_group marker was tried and
explicitly REJECTED for this exact test (T-0760/T-0759) -- reasoning:
"a serial/xdist-group marker was rejected because pytest-xdist has no
mechanism to pause OTHER files' workers while one test runs, so it
would not have removed the contention this ticket reproduced." Pinning
this test alone to a dedicated xdist group does not stop OTHER test
files' workers from contending for the same physical cores, so it
would not address the measured 0.54 overhead's actual cause (host
oversubscription). Whoever picks this up should weigh that documented,
already-evaluated tradeoff before choosing between the two options this
ticket offers.


frob:waive BUG002 reason="the sampled overhead assertion is a nondeterministic host-contention flake (measured 0.5382 under gw3 in run 33513484322, comfortably under the tolerance most of the time including at main's HEAD) -- it cannot be made to fail-at-parent/pass-at-fix deterministically in a local repro since the failure depends on transient host oversubscription this environment cannot reliably recreate. This is the same nondeterministic-crash class BUG002's own guidance names as waivable."