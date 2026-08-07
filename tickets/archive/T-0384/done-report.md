## Done report

Reconciled docs/design/registry/weaknesses.yaml (944 CWE-1000-View entries +
40 other-framework entries = 984 total) against actual enforcement. Ran the
real registry loader/audit over the file: 16 handled_by, 27 deferred, 143
duplicate-of, 798 out-of-scope, 0 unaccounted, 0 malformed -- fully exhausted
already at the disposition level, except all 27 deferred entries dishonestly
named T-0384 itself (this review-gated reconciliation ticket, expected to
close), which would break REG003 the moment it closes.

Filed a new standing ticket (drafted off-main as T-0684 (ex-draft, id lost at land); drafts do
not survive `frob ticket land`, T-0577, so a real id replaces it at land time
-- same precedent as T-0388/T-0607) and re-pointed all 27 self-deferring
entries (CWE-20/22/77/78/79/89/94/119/125/190/269/276/287/306/352/362/416/
434/476/502/639/787/798/862/863/918/922) to it. These 27 overlap the CWE
Top-25/OWASP classic set and are exactly what T-0674 (Top-25 tension, blocked
on this ticket) will need to look at -- noted for that ticket, not acted on
here.

Added tests/test_registry_reconciliation_weaknesses.py (8 tests, all real
data, no fixtures): file loads under the unified model with zero malformed
entries, declared cwe_total pinned at 944, audit reports exhausted with the
984 grand total (944 CWE + 40 other-framework), every deferred entry
resolves to a real non-done ticket in the live queue, no entry defers to
T-0384 itself, and registry_gate raises zero violations for weaknesses.yaml
specifically. Added to ticket scope before recording evidence per the
T-0385 precedent.

`uv run frob check --ticket T-0384` is clean (0 errors, ruff/ty/gate-summary
all pass). No re-pointing regressions found in sibling registries; only this
file's self-deferral was touched.

### Changed
```
 docs/design/registry/weaknesses.yaml             |  54 +++---
 tests/test_registry_reconciliation_weaknesses.py | 202 +++++++++++++++++++++++
 2 files changed, 229 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_declared_cwe_total_is_944` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations` (pytest node id, verified passing when recorded)
