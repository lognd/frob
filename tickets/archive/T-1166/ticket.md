---
id: T-1166
title: 'strata: serve daemon now exercises real net/fs effects directly -- capability-boundary
  disposition needed (T-0440 regression)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- src/frob/strata/**
- tests/unit/strata/test_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
designated_repro_test: null
threat: null
component: null
---
Found while triaging T-1006 (widespread pre-existing test failures).
tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
fails -- and per its own docstring (T-0440), this is EXACTLY what it is
designed to catch, not a stale expectation: it asserts `serve` is a
deliberately zero-`may` node, delegating every net/fs/exec effect to
code bound on another node via flow edges rather than calling
open/subprocess/socket directly from src/frob/serve/**.

check_capability_conformance now reports 6 real undeclared effects, all
newly introduced (T-1094 FS-watch push invalidation, T-1096
subscribe/push event stream over the socket -- both landed since this
test last passed):

  src/frob/serve/_events.py:169  net.connect (socket.)
  src/frob/serve/_events.py:177  fs.write (.write()
  src/frob/serve/_socketd.py:166 fs.write (open()
  src/frob/serve/_socketd.py:494 fs.write (.write()
  src/frob/serve/_socketd.py:534 fs.write (.unlink()
  src/frob/serve/_socketd.py:663 net.connect (socket.)

This needs a real architecture/security disposition, not a test patch:
either (a) `serve`'s design-model node should legitimately declare
`may net.connect`/`may fs.write` now that the daemon owns the socket/FS-
watch push machinery directly (with a docstring justifying the widened
trust boundary), or (b) the socket/FS-write plumbing in _events.py/
_socketd.py should be refactored to delegate through an existing
may-bearing node (core/gates/graphlang/tickets_ledger) the way every
other serve-side effect already does, preserving the zero-may
invariant. Deliberately not decided under T-1006 -- this is a security-
boundary call, not a stale-fixture fix, and out of T-1006's declared
scope (tests/**, not src/frob/serve/** or the strata design model).