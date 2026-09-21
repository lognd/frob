---
id: T-5229
title: test_drain.py _fake_probe missing whole_land kwarg (fixture drift, blocked
  by T-5035 lease)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
blocked_by:
- T-5035
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_drain.py
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
Split off T-5247 due to a live lease collision (T-5035 holds tests/unit/verify/test_drain.py). tests/unit/verify/test_drain.py::TestRunDrainAsync::test_excludes_its_own_originating_land_pid fails: _fake_probe(root, *, quiet, exclude_pid=None) does not accept the whole_land kwarg the real _probe_land_once call at src/frob/tickets/_leases.py:3089 now passes -- TypeError. Fix: add whole_land=False to _fake_probe's signature, same shape as T-5245's already-landed fix for the analogous _force_zero_wait drift. Wait for T-5035 to release its lease (or land) before starting this.