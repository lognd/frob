---
id: T-2551
title: 'COV007 is mis-scoped for files with no public surface: 78 findings in scripts/
  and .claude/hooks/'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- frob.toml
- tests/unit/gates/test_cov007_entrypoint_exemption.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: the exemption is keyed on frob.toml's [[refs.entrypoint]] declarations,
    so the four executable declarations move with the gate change
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/gates/test_cov007_entrypoint_exemption.py
  reason: both-direction controls live in their own file because tests/test_gates.py
    is under T-2543's live lease
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_same_file_undeclared_still_fires
- tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_library_module_still_fires_when_another_file_is_declared
designated_repro_test: tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
designated_repro_changes:
- old_value: tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_declared_entrypoint_executable
  new_value: tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
  reason: the original designation named a tests/test_gates.py node; that file is
    under T-2543's live lease, so the controls moved to their own file and the repro
    id moved with them
  actor: logan
  at: '2026-08-18'
evidence_changes:
- old_node: tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_declared_entrypoint_executable
  new_node: tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
  reason: the control moved out of tests/test_gates.py, which is under T-2543's live
    write lease
  actor: logan
  at: '2026-08-18'
- old_node: tests/test_gates.py::TestCoverageGate::test_cov007_fires_for_the_same_file_when_it_is_not_declared
  new_node: tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_same_file_undeclared_still_fires
  reason: the control moved out of tests/test_gates.py, which is under T-2543's live
    write lease
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6b0e24abb5803ac52872c5287e2d5447e5c40dbc
---
78 of COV007's 139 live findings sit in files that have no public API
surface at all, so the rule's stated remedy is unachievable there:

  scripts/fleet_status.py                    40
  .claude/hooks/root-write-guard.py          28
  .claude/hooks/root-cleanliness-detector.py  6
  .claude/hooks/_agent_context.py             4

These are standalone executables (a coordinator script, three git/agent
hooks). Their entire callable surface is `main()` plus module-private
helpers and constants by deliberate convention -- several of them
(`scripts/fleet_status.py`) additionally contract to import nothing from
`frob` at all. COV007 tells each one to "move it onto the public caller";
there is no public caller, and moving 40 per-constant anchors onto
`main()` would collapse 40 distinct doc obligations into one and destroy
the per-symbol digest binding that makes AFFECT001/DRIFT001 fire when the
documented thing changes. Following the rule would make the doc graph
strictly worse.

A rule that fires on 100% of the documented symbols in a file class, with
a remedy that class cannot perform, is mis-scoped rather than right-and-
noisy.

OPTIONS (owner decision):
- scope COV007 to library source roots (src/**), the only place a
  "public API surface" exists to move an anchor onto;
- or treat a module with NO public symbols at all as out of scope for
  COV007, which is the same rule stated structurally;
- or leave it and accept 78 boilerplate waivers, which is the outcome
  this repo has already reached ~100 times for the same code (see the
  identical T-1636/T-0871 COV007 waiver texts repeated across
  _land_cmd.py, dup/_core.py, doctor.py, ...).

Filed from T-2370's triage. Does NOT block T-2370's zero half by itself,
but T-2370 cannot reach zero -- and so must not be promoted to ERROR --
until this and T-2549 are decided.