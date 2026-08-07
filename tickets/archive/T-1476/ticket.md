---
id: T-1476
title: 'arch: LARGE001 split of vet _capability python family (T-1420 delivered portion
  6)'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_python.py
- src/frob/vet/_capability_core.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
designated_repro_test: null
threat: null
component: null
---
Leaf carrier for T-1420's sixth delivered portion. Implements step 2 of the
T-1459 vet _capability split design: the python import/binding-aware
resolution family (scope binding, alias table construction, resolved-
candidate collection, `_python_binding_capabilities`/
`_python_binding_operations`) moved verbatim from src/frob/vet/_capability.py
into a new sibling src/frob/vet/_capability_python.py (5513 -> 4670 lines;
new file 867 lines). `_capability.py` imports the three externally-used
names (`_python_binding_capabilities`, `_python_binding_operations`,
`_python_resolved_candidates`) back from `_capability_python` so the public
surface (scan_file_capabilities/language_for/non_executable_line_numbers)
is unchanged.

`_needle_matches_resolved` (used by every per-language family, not
python-specific despite its T-0328 origin) was relocated to
`_capability_core.py` instead of `_capability_python.py` -- it is called
from the TS/rust/C/kotlin blocks still in `_capability.py` too, so putting
it in the python sibling would have made those families import from a
python-named module. This keeps the design's "core imports from no
per-language module" rule intact.

The one frob:waive PERF008 sitting inside the moved python range carried
verbatim into `_capability_python.py`. All 14 other pre-existing waivers
remained in `_capability.py` untouched.

Verification: `pytest tests/test_vet.py tests/test_vet_capability.py`
all passing (targeted, foreground). `frob check --only archgate --only
dead_symbols`: 0 errors. `frob check --only wire --ticket T-1420`: 0
errors. `frob check --only drift --only invariant --only doclink`: 0
errors. `frob check --only pii_structural --only fmt --ticket T-1420`:
0 errors. ruff check/format clean on all three touched files
(_capability.py, _capability_python.py, _capability_core.py).

Steps 3-6 of the T-1459 design (typescript/rust/c/kotlin families) are
NOT done this session -- left for the next T-1420 session.