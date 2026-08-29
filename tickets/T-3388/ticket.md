---
id: T-3388
title: 'SELFAUDIT001: refactor node exec via-list has no ratchet lock entry'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/capability-via-ratchet.lock.json
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
gate:SELFAUDIT (SELFAUDIT001) reports:

  self-audit family SYS111 node=refactor: exec via-list on refactor grew
  to 1 site(s), above the committed ratchet ceiling of 0

design/frob.strata already declares (with an explanatory comment around
line 1035-1039) may "exec" via "src/frob/refactor/_verify.py"; on the
refactor node, but docs/design/registry/capability-via-ratchet.lock.json
has no "refactor::exec" entry at all, so it defaults to a ceiling of 0.
This is pre-existing drift, unrelated to T-3386 (testsuite node fix) --
confirmed by git log on both files showing no recent touch to the
refactor node's exec declaration.

Fix: add a "refactor::exec" entry to the ratchet lock with
accepted_count=1 and a real reason, same shape as other entries (see
"testsuite::exec" for the pattern), OR determine whether refactor's exec
grant should be removed/tightened instead.

Filed while working T-3386 (SUPPRESS001/SELFAUDIT001 gate-visibility
sprint); do not fix inside T-3386, which is scoped to design/frob.strata
plus the testsuite ratchet entry only.
