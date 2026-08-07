## Done report

## Done report

Changed:
- src/frob/gates/__init__.py::_cov001
- src/frob/gates/__init__.py::_cov002_check_symref

Set `symref` on COV001 and COV002 violations (both are precisely about ONE
symbol) so `_match_waiver` uses its symbol-exact matching mode instead of
falling back to file-scoped matching. Before this fix, one `frob:waive
COV001`/`COV002 reason="..."` placed anywhere in a file blanket-suppressed
the same rule for every OTHER symbol in that file, not just the one it was
written above.

Out of scope, intentionally not touched: INV001/INV005 and DRIFT/other
symref-less rules named in docs/audits/gates-accounting.md's B11 finding as
candidates ("etc") -- those checks operate over an invariant id or a whole
module/interface, not a single code symref the way COV001/COV002 do
(INV001's own existence-vs-proof gap is a separate finding, B12). Scoping
this fix to COV001/COV002 keeps the change reviewable and matches what B11
actually demonstrates broken.

Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov001_waiver_does_not_blanket_suppress_sibling_symbol
- tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports (regression, unchanged)

Filed: none

Gates: uv run frob check --delta --ticket T-0553 clean (0/136 new violations);
uv run pytest tests/test_gates.py -q: 250 passed (full file)

### Changed
```
 src/frob/gates/__init__.py | 47 ++++++++++++++++++++++++++----------
 tests/test_gates.py        | 59 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 28 ++++++++++++++++++++--
 3 files changed, 119 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov001_waiver_does_not_blanket_suppress_sibling_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports` (pytest node id, verified passing when recorded)
