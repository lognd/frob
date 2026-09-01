---
id: T-3612
title: narrow LandInProgress to the ledger-splice critical section for tickets-dir
  writers
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: high
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
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
Filing verbs (new/drop/body/scope/fail) write only the tickets dir yet
are refused with LandInProgress for a land's ENTIRE multi-minute
duration (flock probe + T-1619 process scan, _leases.py:2017+). The
actual race they guard is the land's ledger SPLICE -- a short critical
section that already runs under tickets.lock.

Fix: scope the refusal to the splice critical section. Ticket-file
writers take tickets.lock (they already do); the land holds tickets.lock
only during its splice; outside that window, filing/dropping during a
land is safe -- the land's splice re-reads the ledger under the lock.
Delete or narrow the whole-land flock probe + process-scan refusal for
these verbs (keep it for a second land). Add a two-process test: a land
in its slow phase (gates) while a file verb succeeds; a land in its
splice while the file verb blocks briefly then succeeds; never a
corrupted ledger. Measure before/after: time-to-file during a busy
fleet drops from unbounded (window starvation) to <2s p95.
