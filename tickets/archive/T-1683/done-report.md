## Done report

Investigated and dropped: this ticket's premise was already fully
resolved by two earlier, independent fixes before this ticket's own work
started -- DEAD001's `Violation.symref` (T-1651/T-1652,
`src/frob/gates/_dead_symbols.py:282`) and OPAQUE001's `Violation.symref`
(T-1659, `src/frob/gates/_opaque.py:155-157`) both already thread the
specific flagged symbol's `path::qualname` through to the `Violation`,
and `_match_waiver`'s symref-exact branch (`src/frob/gates/_waive.py`)
already binds a `frob:waive DEAD001`/`frob:waive OPAQUE001` comment to
that ONE symbol, not the whole file. Verified directly: both rules'
existing regression tests pass unmodified on the current tree
(`tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it`,
`tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref`,
`tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file`).
No remaining gap found in either rule.

frob:no-behavior-change reason="dropped, no code changed -- the fix this ticket asked for was already landed by T-1651/T-1652 (DEAD001) and T-1659 (OPAQUE001) before this ticket's own work started; bound evidence is the pre-existing regression tests proving the already-fixed behavior, not a repro of a live defect"

### Changed
```
 tickets.md | 38 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
