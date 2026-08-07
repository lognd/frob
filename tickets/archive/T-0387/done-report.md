## Done report

Reconciled docs/design/registry/pii.yaml (7 catalogued entries) against
actual enforcement. All 7 entries already carried a real disposition
(landed generically via T-0407 unified Registry model + T-0426 backlog
drain): all 7 are handled_by:PII010 (GDPR special categories, CCPA
categories, HIPAA safe-harbor identifiers, PCI DSS glossary terms, NIST
800-122 definition, detectable-shapes crossmap, and the standard PII
category reconciliation table), each encoded structurally by
src/frob/gates/_pii_structural.py's PII010/SEC110 field-signature scan.
Zero undispositioned (REG001), zero dangling handled_by/deferred/
duplicate_of targets, zero malformed entries. `uv run frob check --only
registry` and `uv run frob check --ticket T-0387` both report 0 registry
errors for this file.

What this ticket added: the file-specific EXHAUSTIVENESS meta-test the
acceptance criterion calls for, over REAL data -- same posture as
tests/test_registry_reconciliation_patterns.py (T-0385) and
tests/test_registry_reconciliation_secrets.py (T-0386). New file
tests/test_registry_reconciliation_pii.py pins: the file loads under the
unified model with zero malformed entries; the declared total (7)
matches audit_registry_file's total; audit.exhausted is True with 0
unaccounted; handled+deferred+duplicate+out_of_scope == 7; every
deferred: entry (none currently exist) names a real, open ticket; and
registry_gate over the real registry dir raises zero violations scoped
to pii.yaml. Wired into the default `frob check` run (gate:registry runs
unconditionally), so a future silent gap in this file fails the build
via both the gate and this test.

No code changes to src/frob/vet/ were needed -- the unified registry
model and gate (src/frob/gates/_registry_exhaustiveness.py,
src/frob/registry/) already generically enforce this file; there is no
pii-specific logic left to write.

### Changed
```
 docs/design/registry/compliance.yaml             |  42 ++---
 tests/test_registry_reconciliation_compliance.py | 185 +++++++++++++++++++++++
 tests/test_registry_reconciliation_pii.py        | 160 ++++++++++++++++++++
 tests/test_registry_reconciliation_secrets.py    | 158 +++++++++++++++++++
 tickets.md                                       |  62 +++++++-
 5 files changed, 587 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_pii.py::TestPiiRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestPiiRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestPiiRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestPiiExhaustiveness::test_declared_total_is_7` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestPiiExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestPiiExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_pii.py::TestExhaustivenessGateOverRealPii::test_no_pii_violations` (pytest node id, verified passing when recorded)
