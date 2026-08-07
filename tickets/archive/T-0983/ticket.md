---
id: T-0983
title: 'frob test: stability-capture pass uses dotted node ids, always collects 0
  and no-ops'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/app/**
- tests/test_app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_app.py
  reason: regression test for the id-conversion fix lives in the existing TestStabilityGate
    suite
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_app.py::TestStabilityGate::test_dotted_symref_converted_to_pytest_node_id
designated_repro_test: null
threat: null
component: null
---
`uv run frob test --base main` (and any command that flows through
`track_python_stability`) runs the touched-set pytest suite TWICE per
invocation: once with real pytest node ids (`file.py::Class::method`,
correctly separated), which passes normally, and a second time to feed
`capture_python_outcomes` for `.frob/test-stability.json` recording. The
second pass' node ids use a dot between the class and method
(`file.py::Class.method`) instead of `::`, which pytest does not
recognize as valid node-id syntax -- it collects 0 tests and exits 5,
so `capture_python_outcomes: captured 0 outcome(s)` /
`record_outcomes: recorded 0 test outcome(s)` every single run.

Repro observed twice in a row while working T-0972 (unrelated PERF
gate ticket): the primary run reports `[PASS] python exit=0` with the
touched-set fully executed, then the stability-capture pass
immediately after logs `returncode=5` and records zero outcomes.

`capture_python_outcomes` (src/frob/testing/_stability.py:520) itself
takes `node_ids` as given and is not the bug; the caller that builds
the second node-id list (something upstream of `track_python_stability`
in the `frob test` CLI path) is passing dotted method names instead of
reusing the same `::`-joined ids the primary pytest invocation used.
`_runners.py:226`'s own `qualname.replace('.', '::')` shows the correct
join already exists elsewhere in this package -- the stability-capture
caller needs the same treatment.

Net effect: `.frob/test-stability.json` has not been updated by a
normal `frob test` run in this repo for as long as this bug has been
live -- stability tracking is silently a no-op.