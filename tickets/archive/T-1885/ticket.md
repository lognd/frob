---
id: T-1885
title: verify_import_resolution ast.parses every touched file with no Python-extension
  filter
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/refactor/_verify.py
- tests/test_refactor.py
- docs/commands/refactor.md
- src/frob/refactor/_models.py
- src/frob/refactor/_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: ticket explicitly asks for a run_refactor regression test proving the fix
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/refactor.md
  reason: AFFECT001 requires updating the affects()-closure doc for verify_import_resolution's
    behavior change
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/refactor/_models.py
  reason: 'coordinator directive: VerifyOutcome must distinguish skipped/not-applicable
    files from a genuine pass, not silently fold them together (T-1664 vocabulary
    spirit)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/refactor/_cli.py
  reason: 'coordinator directive: VerifyOutcome must distinguish skipped/not-applicable
    files from a genuine pass, not silently fold them together (T-1664 vocabulary
    spirit)'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_refactor.py::TestVerify::test_import_resolution_skips_non_python_touched_file
- tests/test_refactor.py::TestVerify::test_import_resolution_still_catches_syntax_error_in_py_file_among_non_py
- tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while writing T-1854's regression tests.
`verify_import_resolution` (src/frob/refactor/_verify.py) calls
`ast.parse` on every path in `touched_files` unconditionally -- no
filter for a `.py` extension. Any `RefactorPlan.reference_ops` entry
touching a non-Python file (a `tickets/<id>/ticket.md`, a
`docs/design/registry/*.yaml`, any prose/doc carrier) makes
`run_refactor`'s Verify phase try to parse that file as Python, fail
(observed: "leading zeros in decimal integer literals are not
permitted" parsing a ticket.md's `T-0001`-shaped id), and roll the
whole transaction back -- even though nothing about the actual rewrite
was wrong.

This means `frob refactor rename`'s existing ticket-evidence carrier
(T-1546, `scan_evidence_citations`) and registry carrier (T-1200,
`scan_registry_citations`) are BOTH silently non-functional through the
real `run_refactor` end-to-end path today whenever they produce a hit
-- confirmed by reproduction, not assumed: a ticket carrying a real
evidence citation for a moving symbol causes `run_refactor` to roll
back. `scan_evidence_citations`/`build_plan` themselves are unaffected
(no verify step runs there), so this was invisible to every existing
scan-level unit test, which is presumably why it was never caught.

Fix: filter `touched_files` to a `.py` suffix before the parse loop, or
skip a file whose suffix cannot possibly be Python source, in
`verify_import_resolution`. Add a regression test that runs a plan
touching a non-Python file (a ticket.md carrier is the simplest real
repro) through `run_refactor` and asserts it does NOT roll back for
this reason.