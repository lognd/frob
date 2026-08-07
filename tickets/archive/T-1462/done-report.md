## Done report

Implemented step 1 of the T-1459 vet _capability split design (T-1420
LARGE001 residue): the scanner-core primitives moved verbatim from
src/frob/vet/_capability.py to a new sibling src/frob/vet/_capability_core.py.
6070 -> 5511 lines; new file 611 lines. Public surface (scan_file_capabilities,
language_for, non_executable_line_numbers, etc) unchanged -- _capability.py
imports every moved name back from _capability_core.

Fixed en route: a dropped `return found` at the tail of
`_matched_capabilities` caught by the targeted pytest run; a new
`_SELF_PATTERN_SUFFIXES` entry for `_capability_core.py` (same
self-scan-exclusion precedent as the T-1420 registry package split);
retargeted `test_capability_module_self_scan_documented_false_positive`
to scan `_capability_core.py` (the `b"compile("` literal it locks moved
there); `frob:waive INV006 preset="split-carried-prose"` on the new
file for its documentation-only "only" claims.

All 16 pre-existing frob:waive directives carried forward (1 into the
new file, 15 stayed). Per-language families (steps 2-6 of the T-1459
design) not attempted this session -- left for the next dedicated
T-1420 session.

### Changed
```
 tickets.md | 76 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 74 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 465 warning(s), 735 waived
- error-findings: DUP001@src/frob/vet/_capability_core.py, SELFAUDIT001@design
