---
id: T-4330
title: 'verify_runner.py: pre-existing SELFAUDIT001/SCOPE002 debt exposed by narrow
  ticket scoping'
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
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
Found while working T-4324 (frob verify status rapid-debt visibility fix).

Two pieces of pre-existing debt on src/frob/app/verify_runner.py surfaced by
`frob check --ticket T-4324`, neither introduced by T-4324's own diff and
neither fixable within that narrow, single-file ticket scope without an
unbounded scope-closure cascade (measured: adding
docs/modules/tickets-verify-sweep.md to scope pulled in ~135 unrelated
doc-anchor warnings; adding design/frob.strata pulled in ~240):

1. SELFAUDIT001: this module's read_text() calls (existing ones, e.g.
   AppConfig loading, plus T-4324's own two new ones) are not declared as
   'fs.read' capability sites for the cli node in design/frob.strata's
   node covering src/frob/app/**. Fix: add src/frob/app/verify_runner.py
   to that node's existing 'may "fs.read" via ...' list (design/
   frob.strata, near line 140) -- a one-line addition, done in its own
   ticket scoped to include design/frob.strata and whatever closure it
   requires there.

2. SCOPE002: several PRE-EXISTING public symbols in this file
   (VerifyQuarantineFindingView, VerifyStatus, build_status, _run_dispose,
   _run_drain_async, run) carry frob:doc targets in
   docs/modules/tickets-verify-sweep.md, and several existing tests carry
   frob:tests targets in src/frob/verify/_quarantine.py -- neither file
   is in this file's own historically-narrow ticket scopes, so any
   ticket scoped to just this one file trips SCOPE002 on baseline debt
   it did not create. Fix direction: either broaden this file's typical
   ticket scope going forward to include its real doc/test dependencies,
   or split docs/modules/tickets-verify-sweep.md's single giant
   frob-verify-cli-t-1697 anchor into a per-symbol/per-file anchor so a
   narrow ticket's scope-closure check does not need the whole shared
   doc.

MEASURED: frob check --ticket T-4324 (scope=['src/frob/app/verify_runner.py'])
showed gate:SELFAUDIT 2 errors and gate:SCOPE 2 pre-existing SCOPE002
findings (7-symbol doc-target gap, 3-symbol test-target gap) that
reproduce on the file's original, unmodified content.
