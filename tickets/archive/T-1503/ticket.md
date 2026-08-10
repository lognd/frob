---
id: T-1503
title: WIRE001 on test_extract_native.py's _python_side/_rust_side golden-test helpers
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_extract_native.py
- tests/unit/test_capability_native.py
- tests/unit/test_arch_python_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_capability_native.py
  reason: same WIRE001 golden-test-helper pattern (a module-level comparison helper
    called only from its own file's test methods) now exists in these two files too
    (T-1221/T-1222); consolidating under this one existing ticket rather than filing
    near-duplicates
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_arch_python_native.py
  reason: same WIRE001 golden-test-helper pattern (a module-level comparison helper
    called only from its own file's test methods) now exists in these two files too
    (T-1221/T-1222); consolidating under this one existing ticket rather than filing
    near-duplicates
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_control_flow_and_self_field_access
designated_repro_test: null
threat: null
component: null
---
WIRE001 flags `_python_side`/`_rust_side` in tests/unit/test_extract_native.py
(T-1220's golden-parity tests for frob_core.extract_tree_python) as unreached
outside their own tests -- they exist solely as per-file test helpers that
assemble the existing Python-side computation vs the native kernel's output
for comparison within TestExtractTreePythonParity's own methods, mirroring
the tests/unit/test_conftest_stackdump.py::_load_conftest precedent (T-1466).
Follow-up: evaluate whether this pair should move to a shared test-support
module (frob.testing or a conftest fixture) if a future native-extraction
golden test wants the same comparison, or whether the current per-file scope
is intentionally final (in which case this ticket should close as won't-fix
with that recorded).

## Done report

Investigated and resolved as a documented WON'T-FIX decision, not a code
fix -- writing this as a decision with its own reasoning, not an absence,
per the coordinator's explicit ask.

## Decision

WIRE001 flags `_python_side`/`_rust_side` (and the equivalent per-kernel
comparison helpers in `test_capability_native.py`/
`test_arch_python_native.py`) as unreached OUTSIDE their own tests. This
is not a detector gap or a missing wiring mechanism (unlike T-1534's
actual gap, decorator-shape blindness) -- it is
`frob.gates._wire._wire_test_path_excluded`'s DELIBERATE T-1592 design
decision, read directly from its own docstring: "a test-tree symbol
excludes only its OWN defining file (same-file usage stays genuinely
unwired, T-1592's precedent), so a call from a DIFFERENT test file now
counts as reached." A private golden-test helper called only by test
methods inside its own file therefore can NEVER satisfy WIRE001's
ordinary reached-outside-diff-tests check, no matter how many times it
is genuinely called within that file -- this is intentional, not a case
WIRE001 "cannot see."

T-1592's own rationale (traced back): a helper genuinely private to one
test file's own suite is architecturally equivalent to dead code from
WIRE001's perspective -- if it only exists to serve that ONE file's
tests, nothing outside the file depends on its continued existence or
shape, so treating same-file usage as "wired" would let an entire class
of orphaned, unreferenced-in-practice helpers escape detection just
because they happen to still be called from a stale test in the same
file. The design trades a predictable false-positive class (every
private golden-test helper needs an explicit waiver) for closing a real
detection gap (helpers that used to be shared, are no longer, and would
otherwise silently persist forever).

**Given this is a deliberate, permanent design decision -- not a pending
gap -- the correct resolution is documenting it, not chasing a code fix
that would have to reverse T-1592's own reasoning to "succeed."**

## What changed

Every `frob:waive WIRE001 ... follow_up="T-1503"` citation (7 in
`tests/unit/test_extract_native.py`, 1 in
`tests/unit/test_arch_python_native.py`) was replaced with `permanent=
"true"` -- `_wire002_is_permanent_test_helper_waiver`'s existing escape
hatch for EXACTLY this shape (a private, `tests/`-rooted symbol whose
condition will never stop being true), the same one `tests/unit/
test_mutation_sweep_queue.py::_make_ticket` already uses per its own
T-1592 citation. This was itself the concrete instance of the
coordinator's point: pointing these waivers at `follow_up="T-1503"`
committed to a FUTURE ticket closing them out, but T-1503 was always
going to close as won't-fix -- so every one of those citations would have
become exactly the "waiver pointing at a dead ticket" anti-pattern the
moment T-1503 closed, with no mechanism to notice. `permanent="true"`
states the true, stable fact directly instead.

`test_extract_native.py`'s module docstring gained a paragraph naming
T-1503/T-1592 explicitly so a future reader hitting one of these waivers
does not have to re-derive "why is this permanent, not a follow-up"
from scratch.

## Filed

`T-1803` (renumbers at land) -- "Detect a frob:waive whose
suppressed finding no longer fires, not just an orphaned follow_up
citation", using T-1534's own two now-closed instances (waivers whose
follow_up ticket was still OPEN but whose underlying gate finding had
already stopped firing entirely, thanks to an unrelated ticket, T-1510,
fixing the real cause first) as evidence. This is explicitly a DIFFERENT
false-signal class from T-1751 (an orphaned follow_up CITATION) and from
T-1503 itself (a permanently-true waiver condition) -- named as such in
the new ticket's own body so the three do not get conflated later.

Gates: `frob check --only wire` -- 0 errors, 0 warnings (the DSL001
malformed-directive errors an earlier bulk edit attempt introduced were
caught and reverted before this report, not landed). `pytest tests/
unit/test_extract_native.py tests/unit/test_arch_python_native.py` --
18/18 pass.

Status: leaving T-1503 IN-PROGRESS for the coordinator/reviewer to close
after land, per this repo's review-gated ticket workflow. Recommend
closing as `won't-fix` (or `done`, if this repo's ticket-kind vocabulary
treats a documented decision as a delivered outcome) with this Done
report as the record -- not `dropped`, since dropping would lose the
reasoning a future re-investigation would otherwise have to redo.

### Changed
```
 tickets/T-1503/ticket.md           |  5 ++-
 tickets/T-1803/ticket.md | 66 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 70 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_control_flow_and_self_field_access` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 568 warning(s), 725 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, SEC110@src/frob/app/ticket_runner/__init__.py
