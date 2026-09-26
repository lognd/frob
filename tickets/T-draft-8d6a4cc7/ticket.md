---
id: T-draft-8d6a4cc7
title: 'natives: wire _git_commit_crate test helper (or retire the WIRE001 waiver)
  after T-5808'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
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
tests/unit/test_natives_build.py::_git_commit_crate carries a
frob:waive WIRE001 (added by T-5808) since it is a test-only helper
with no caller outside its own tests -- the same shape as this file's
pre-existing _make_crate_dir, just newer, so WIRE001's own diff-added
detection still flags it once T-5808 closes and its follow_up must
point somewhere real.

Two ways to close this:
1. Wire it: give _git_commit_crate a real non-test caller (e.g. reuse
   it from a natives-build integration/system test outside this file),
   or fold it into a shared test-support module other suites can import
   from.
2. Retire the waiver: if no second consumer ever materializes, remove
   the frob:waive WIRE001 directive and accept whatever the gate does
   at that point (inline the body at each of its 4 call sites, or leave
   it as a bare private helper if WIRE001's own rules have grown an
   explicit test-helper exemption by then).
