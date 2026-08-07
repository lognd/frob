---
id: T-1462
title: 'arch: LARGE001 split of vet _capability scanner core (T-1420 delivered portion
  5)'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed
designated_repro_test: null
threat: null
component: null
---
Leaf carrier for T-1420's fifth delivered portion. Implements step 1 of the
T-1459 vet _capability split design: the scanner-core primitives
(pattern compilation, comment/docstring/non-executable byte-span
computation, needle-matching primitives, embedded-code detection family,
and the two dispatch-facing matchers _matched_capabilities/
_operation_entry_matches that only depend on core primitives) moved
verbatim from src/frob/vet/_capability.py into a new sibling
src/frob/vet/_capability_core.py (6070 -> 5511 lines; new file 611
lines). _capability.py imports the moved names back from
_capability_core so the external public surface
(scan_file_capabilities/language_for/non_executable_line_numbers/etc)
is unchanged. Per-language families (python/typescript/rust/c/kotlin,
steps 2-6 of the design) are NOT done this session -- left for the next
T-1420 session, design already recorded in T-1459.

Fixed during implementation:
- A dropped `return found` at the tail of `_matched_capabilities` during
  the move (caught by the targeted pytest run, not by ruff/mypy since the
  function's declared return type made the None fall-through look
  syntactically fine).
- `_SELF_PATTERN_SUFFIXES` (the self-scan-exclusion allowlist
  `_scan_directory_capabilities` consults, T-0910 lineage) needed a new
  entry for `_capability_core.py` -- it now carries the
  `_has_bare_compile_call` needle-as-data self-match hazard the parent
  file used to alone. Same precedent as the T-1420 registry-package split.
- `tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive`
  retargeted from `_capability.py` to `_capability_core.py` -- the
  `b"compile("` code-level literal this test locks moved with
  `_has_bare_compile_call`.
- `frob:waive INV006 preset="split-carried-prose"` added to
  `_capability_core.py` -- the module's several documentation-only
  "only" exclusivity claims (byte-span/needle-matching prose) have no
  enforced algorithmic invariant of their own to bind, same class as
  every other split-carried-prose INV006 waiver in this repo.

Verification: `pytest tests/test_vet.py tests/test_vet_capability.py`
all passing (targeted, foreground). `frob check --only archgate --only
wire --only dead_symbols`: 0 errors (gate:ARCH 0/0/62, gate:DEAD
0/1/43, gate:LARGE 0 errors/47 warnings/1 waived -- both
`_capability.py` and `_capability_core.py` off the LARGE001 error
class, LARGE001 is warning-severity). `frob check --only invariant
--only doclink --only docanchor --only fmt --only pii_structural`: 0
errors after the INV006 waiver. ruff check/format clean on all three
touched files.

All 16 pre-existing frob:waive directives in the original
_capability.py carried forward (1 moved into _capability_core.py, 15
remained in _capability.py) -- confirmed by waiver count before/after.