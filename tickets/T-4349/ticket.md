---
id: T-4349
title: Scaffold check fails collection with an empty stderr tail, the sole linux failure
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
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
ONE TEST STANDS BETWEEN THE LINUX LEG AND A GREEN SUITE, AND IT FAILS WITH AN
EMPTY DIAGNOSTIC.

MEASURED. The linux leg reports 13,823 collected, 1 failed. The failure is the
scaffold test asserting that a freshly-scaffolded python project passes its check
immediately. Inside that scaffold, the coverage gate reports collection failure:

  COV003: pytest collection itself failed -- every Python evidence id is
    unresolved as a consequence of this ONE root cause
  <repo>/.venv/bin/python -m pytest --collect-only -q -o addopts= (cwd=.) exited 2
  stderr tail:
  <nothing>

THE EMPTY STDERR TAIL IS THE FIRST THING TO FIX, BEFORE THE FAILURE ITSELF. A
collection that exits 2 and reports nothing is unactionable, and this project has
repeatedly paid for a diagnostic that produces nothing at the moment it is needed.
Whatever the underlying cause, capturing and surfacing what the failed collection
actually said is the change that makes this and every future instance debuggable.
Do that first and quote what it reveals.

THE LIKELY CAUSE IS A RECENT AND DELIBERATE CHANGE. A ticket landed today that
removed the project runner from frob's own test-collection spawn, invoking the
running interpreter directly instead. That was the correct fix for a
platform-divergent failure and should not be reverted. But it changes which
interpreter collects inside a SCAFFOLDED project: the scaffold is a fresh, separate
project with its own expectations, and collecting it with the outer repository's
interpreter is a different operation from what happened before. Establish whether
that is what is failing here rather than assuming it -- the empty stderr is
precisely why nobody can say yet.

DECIDE WHAT COLLECTING A SCAFFOLD SHOULD MEAN. A newly scaffolded project has no
installed environment of its own; the test asserts it passes a check immediately.
So either the check must collect that project in a way that works with no
environment, or the scaffold must provide enough for collection to succeed. Both
are defensible; pick one deliberately and record why. Do not make the test pass by
weakening what it asserts -- the point of the test is that a new project is usable
out of the box.

VERIFY ON LINUX, where it reproduces, and quote the suite counts. Also confirm you
have not broken the platform fix that caused this: the change that removed the
project runner from the collection spawn exists to keep the macos leg working, so
whatever you do must not reintroduce a dependency on that runner.

The unscoped gate is currently at ZERO errors on main; do not regress it. Note it
has returned different results for the same commit under load (T-4343, open), so
re-run before believing a surprising reading.
