---
id: T-2451
title: _sigterm_handler is genuinely wired via signal.signal (WIRE001 follow_up anchor)
state: queued
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/process/_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: true
anchor_reason: 'Permanent WIRE001 follow_up anchor for frob.process._reap._sigterm_handler.

  The waive directive at src/frob/process/_reap.py:144 cites T-2451 as its

  follow_up target because the best-effort callgraph cannot trace a name

  passed into signal.signal() as a caller (same gap class as T-1831/T-1024).

  There is nothing to implement -- the handler is genuinely wired and covered

  by tests/unit/test_process_reap.py::TestInstallSigtermReaper. WIRE002

  requires a real, non-terminal ticket id as the follow_up target, so this

  ticket must stay open forever rather than land to done/dropped -- landing

  it would orphan the citation (LiveTrackerCited, T-1853''s precedent).

  '
land_commit: null
---
`frob.process._reap._sigterm_handler` is genuinely wired -- passed as the
handler argument to `signal.signal(sigterm, _sigterm_handler)` in
`install_sigterm_reaper` (the very next function in the same module),
then invoked by the interpreter's own signal-dispatch machinery on a
real SIGTERM, never called directly by name from Python code. The
best-effort callgraph (`frob.graph.callgraph`) cannot trace a name
passed into a stdlib registration call (`signal.signal`) as a caller --
the same class of gap as T-1831 (`_GroupedHelpFormatter`'s
`formatter_class=` case) and this repo's cross-package DEAD001 waivers
(T-1024 precedent) applied to WIRE001 instead.

This is a WIRE001 follow_up anchor, not real deferred work: there is
nothing to implement, the code is already correctly wired and covered by
tests/unit/test_process_reap.py::TestInstallSigtermReaper. Left open
only because WIRE002 requires a real ticket id outside tests/ trees.
