---
id: T-3373
title: T-3191's multi-platform ty union triples SUPPRESS001 findings for a cross-platform
  diagnostic
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_suppress.py
- tests/test_gates_suppress.py
- tickets/T-draft-0259dd22/ticket.md
- tickets/T-draft-ffaf100c/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_suppress.py
  reason: own test suite, evidence lives here
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-draft-0259dd22/ticket.md
  reason: same-branch sibling ticket filings, benign passenger, avoids SCOPE001
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-draft-ffaf100c/ticket.md
  reason: same-branch sibling ticket filings, benign passenger, avoids SCOPE001
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
acceptance:
- text: given a mypy-suppressed line where ty reports the SAME unsuppressed diagnostic
    on all 3 target platforms, when suppress001_gate runs, then it reports exactly
    one SUPPRESS001 violation for that file:line:code, not one per platform
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Root-caused live (Series EF, re-measuring chunk3a):
tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
fails with 'assert 3 == 1' on current main.

T-3191 (already landed, unrelated regression source -- not filed against
T-3191 itself since ITS OWN change is working exactly as designed)
changed frob.check._python._run_ty to invoke 'ty check' ONCE PER TARGET
PLATFORM (linux/win32/darwin) and _merge_ty_results unions all three
platforms' diagnostics into one list, each individually tagged
'[platform=<name>]' -- deliberate, so a platform-only finding is
attributable (see that function's own docstring). For a genuinely
cross-platform diagnostic (the SAME file:line:code on all 3 platforms,
the common case), the union now legitimately contains 3 near-identical
Diagnostic entries differing only in their message's platform tag.

frob.gates._suppress._ty_diagnostics reads result.diagnostics and
appends (relfile, line, code) for EVERY entry with no dedup -- pre-T-3191
this was safe because ty ran once, so one diagnostic always meant one
(file, line, code) tuple. Now the same location can appear up to 3
times. _suppress001_correlate then iterates oracle_diagnostics['ty']
directly with no dedup either, appending one Violation per occurrence
-- so a single genuinely-cross-platform mismatch now fires 3
SUPPRESS001 violations instead of 1.

Fix direction: _ty_diagnostics should deduplicate its (relfile, line,
code) output before returning -- SUPPRESS001's whole question is 'does
ANY dialect report this unsuppressed here', a presence check, not a
per-platform count; the platform-attribution T-3191 added is still
fully preserved in the underlying ty ToolResult/Diagnostic objects for
every OTHER consumer (the ty gate's own report), this is scoped to the
one downstream consumer (_ty_diagnostics/suppress001_gate) that
implicitly assumed single-invocation cardinality.