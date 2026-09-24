---
id: T-5471
title: test_packs auto-injection assertion fails on CI (macos) but not locally
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing on macos
(and ubuntu CI) but does NOT reproduce locally in this checkout:
tests/unit/strata/test_packs.py::TestAutoInjection::test_trusted_component_without_pack_gets_it_injected

test_packs's own captured log line ("module design: trusted component
present without std.policy.analyzable; auto-injecting mandatory base
pack") fires in BOTH the failing (CI) and passing (local) runs, so this
looks like an assertion-content mismatch that is state/ordering-sensitive
rather than a clean deterministic pass/fail -- possibly module-iteration-
order dependent (dict/set ordering) or fixture-isolation dependent.

Needs investigation with the exact CI failure text (not available locally
since it does not reproduce here) -- validate any fix against the CI
(macos) failure directly, not just local green, since local green does not
currently mean the bug is absent.
