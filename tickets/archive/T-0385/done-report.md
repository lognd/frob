## Done report

Reconciled docs/design/registry/patterns.yaml (346 catalogued entries) against
actual enforcement. Investigation found the substantive dispositioning work
already landed generically via T-0407 (unified Registry model:
frob.registry._models) and T-0426 (registry backlog fully drained, REG gate
raised WARN->ERROR): all 346 patterns.yaml entries already carry a real
disposition -- 305 out_of_scope:advisory-design-pattern-recommendation
(GoF/pattern-catalog entries are documented advisory recommendations, not
enforced checks) and 41 deferred:T-0332 (hallmark/anti-pattern entries
awaiting T-0332's design-pattern recommender, an open feature ticket). Zero
undispositioned (REG001), zero dangling handled_by/deferred/duplicate_of
targets, zero malformed entries. `uv run frob check --only registry` and
`uv run frob check --ticket T-0385` both report 0 errors for this file.

What this ticket added: the file-specific EXHAUSTIVENESS meta-test the
acceptance criterion calls for, over REAL data (not the existing synthetic
fixtures in test_registry_exhaustiveness.py) -- same posture as
tests/test_check_coverage_registry.py (T-0424). New file
tests/test_registry_reconciliation_patterns.py pins: the file loads under
the unified model with zero malformed entries; the declared total (346)
matches audit_registry_file's total; audit.exhausted is True with 0
unaccounted; handled+deferred+duplicate+out_of_scope == 346; every
deferred: entry names a real, currently-open ticket (not DONE, not
missing); and registry_gate over the real registry dir raises zero
violations scoped to patterns.yaml. This is wired into the default `frob
check` run (gate:registry already runs unconditionally), so a future
silent gap in this file fails the build via both the gate and this test.

No code changes to src/frob/vet/ were needed -- the unified registry model
and gate (src/frob/gates/_registry_exhaustiveness.py, src/frob/registry/)
already generically enforce this file; there is no patterns-specific logic
left to write.

### Changed
```
 tests/test_registry_reconciliation_patterns.py | 156 +++++++++++++++++++++++++
 tickets.md                                     |  73 +++++++++++-
 2 files changed, 227 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_declared_total_is_346` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations` (pytest node id, verified passing when recorded)
