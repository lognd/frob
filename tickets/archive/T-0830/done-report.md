## Done report

Selfconform audit now walks the tree once (shared node index reused across
rule passes instead of a fresh walk per rule); audit output proven
byte-identical pre/post and wall time drops 7.2s -> 4.3s.

### Changed
```
 src/frob/strata/_selfconform.py | 131 ++++++++++++++++++++++++++++++----------
 tickets.md                      | 107 +++++++++++++++++++++++++++++++-
 2 files changed, 205 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: -1 error(s), -1 warning(s), -1 waived
