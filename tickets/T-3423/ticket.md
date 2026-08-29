---
id: T-3423
title: test_parses_and_elaborates freezes model counts by hand and has now drifted
  a fourth time; its docstring records the prior three
state: done
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
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: declare scope on this test file before editing per T-3423's instructions
  actor: logan
  at: '2026-08-29'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModelFailureModes::test_unparseable_source_fails_to_parse
- tests/system/test_frob_self_model.py::TestFrobSelfModelFailureModes::test_empty_module_elaborates_but_fails_every_surface_assertion
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_golden_node_id_set_catches_an_injected_node
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_golden_node_id_set_catches_a_removed_node
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_golden_node_id_set_passes_when_unchanged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6f26c00d159c21465eaa742449de8a8dda74fa48
---
`TestFrobSelfModel::test_parses_and_elaborates` asserts hard-coded node, flow
and claim counts for the design model, so every legitimate model change breaks
it. It has now drifted at least four times, and its own docstring is the record
of the previous three.

MEASURED 2026-08-29, serial tests/system run on an idle box without coverage
instrumentation:

    tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
    FAILED

This is the same file reported as segfaulting in an earlier session and never
successfully measured until now, so the failure is newly VISIBLE rather than
newly introduced.

THE DOCSTRING IS THE EVIDENCE. It narrates three prior drifts in sequence:

  T-0440  split deploy/serve/mutate off core's utility hub. The docstring
          records that counts were ALREADY stale BEFORE that ticket touched
          them (12/32/24 measured directly via elaborate, against 10/27/23
          asserted), because T-0707's `may "exec"` addition and its
          CWE-78 discharge claim were never folded in. Disclosed as
          pre-existing debt in that Done report rather than fixed.
  T-0967  same drift again from T-0864's `natives` node: +1 node, +2 flows,
          +1 THREAT003 claim, again never folded in.
  T-1079  same again, via SYS103's follow-up.

Four separate tickets have now paid the cost of updating hand-maintained counts
that no human reads and no consumer depends on. T-3413 moved them again by
adding `frob.nodeid` to `core`'s code= glob -- a correct change that this test
punishes.

WHAT THE TEST IS ACTUALLY FOR. Its own summary line says: "Sanity: the model
declares a nonzero component/flow/boundary/claim surface." That is a real and
worthwhile property -- it catches a model that fails to load, or that elaborates
to nothing. Exact equality against frozen integers is a much stronger claim than
that sentence, and it is the stronger claim that keeps breaking.

THE DECISION TO MAKE, explicitly:
  (a) Assert the stated property -- nonzero, and structurally coherent -- and
      drop the frozen integers. Cheapest, matches the docstring's own
      description, and loses the ability to notice an unintended count change.
  (b) Keep exact counts but generate them, so the assertion is derived from the
      model rather than transcribed by hand. Turns drift into an automatic
      update and keeps change-detection, but a self-updating assertion detects
      nothing unless something else reviews the delta.
  (c) Keep exact counts and accept the maintenance, but make the failure
      message say "the model changed, update these numbers and confirm the
      change was intended" so the next person is not archaeology-hunting.
I lean (a) plus a separate explicit check for whatever property genuinely needs
guarding, but the choice is a real one -- state the reasoning rather than
inheriting mine.

DO NOT simply update the integers to today's values and close this. That is
what the previous four tickets did, and it is why this is being written a fifth
time. If the numbers ARE updated as an interim step, say plainly that the
underlying pattern is unaddressed.

DO NOT delete the docstring's drift history when fixing. It is the only record
that this has recurred, and it is the argument for changing the approach.

MUST-FIRE FIXTURE:   a model that fails to elaborate, or elaborates to an empty
                     surface, still fails this test.
MUST-STAY-QUIET:     adding a legitimate node to the model does not fail it
                     (under (a) or (b)); under (c), it fails with a message
                     naming what to update and why.

ACCEPTANCE
- The chosen option stated with reasoning.
- The drift history preserved.
- Both fixtures present.