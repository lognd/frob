## Done report

Confirmed CMPL-FROB-CATALOG-ENTRIES is NOT the vacuous self-reference
shape T-1244 flagged: it is a real meta-row counting COMPLIANCE_CATALOG's
own RegulationEntry units, each independently wired into
check_regulation_catalog_completeness/check_regulation_discharge
(COMPLIANCE001-003) with a real mitigation, distinct from this row's own
disposition string. Stated that explicitly in a comment on the row so it
is not silently swept into the T-1245-1249 re-triage bucket.

Corrected the stale leaf_count (6 -> 7) and total_leaf_controls_enumerated
(599 -> 600): COMPLIANCE_CATALOG grew to 7 entries when T-1314 added
PRIVACY-NOTICE, and this registry row had gone stale. docs/design/
compliance-corpus.md's own upstream manifest (count: 6,
TOTAL_LEAF_CONTROLS_ENUMERATED: 599) is now ALSO stale by the same +1 but
is outside this ticket's scope (docs/design/registry/compliance.yaml,
src/frob/strata/_compliance.py only) -- filed T-1324 to correct
it rather than silently editing an out-of-scope file.

Resumed from an OOM-killed prior session; this session verified the
already-drafted fix, confirmed the draft ticket exists, ran the full
compliance test file, and merged main forward with no scope regression.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  43 +--
 docs/design/registry/compliance.yaml        |  95 ++++---
 docs/modules/gates.md                       |  33 ++-
 docs/strata/threat.md                       |  11 +
 src/frob/gates/_sys.py                      | 124 ++++++++-
 src/frob/strata/_compliance.py              |  40 ++-
 tests/test_gates.py                         |  76 ++++++
 tests/unit/strata/test_compliance.py        |  22 +-
 tickets.md                                  | 397 ++++++++++++++++++++++++++--
 9 files changed, 754 insertions(+), 87 deletions(-)
```

### Evidence
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_frob_catalog_entries_self_reference_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 395 warning(s), 678 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
