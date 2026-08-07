## Done report

Reconciled docs/design/registry/secrets.yaml (3 catalogued entries) against
actual enforcement. All 3 entries already carried a real disposition
(landed generically via T-0407 unified Registry model + T-0426 backlog
drain): 1 out_of_scope (SEC-SECRETS-SECRETS-DETECTOR_PROJECTS, a
bibliographic census of external tools frob does not vendor) and 2
handled_by:SEC001 (the DETECT_SECRETS_PLUGINS and PROVIDER_TOKEN_FORMATS
entries, both encoded by the _PATTERNS regex table in
frob.gates._secrets). Zero undispositioned (REG001), zero dangling
handled_by/deferred/duplicate_of targets, zero malformed entries.
`uv run frob check --only registry` and `uv run frob check --ticket T-0386`
both report 0 registry errors for this file.

What this ticket added: the file-specific EXHAUSTIVENESS meta-test the
acceptance criterion calls for, over REAL data -- same posture as
tests/test_registry_reconciliation_patterns.py (T-0385). New file
tests/test_registry_reconciliation_secrets.py pins: the file loads under
the unified model with zero malformed entries; the declared total (3)
matches audit_registry_file's total; audit.exhausted is True with 0
unaccounted; handled+deferred+duplicate+out_of_scope == 3; every
deferred: entry (none currently exist) names a real, open ticket; and
registry_gate over the real registry dir raises zero violations scoped
to secrets.yaml. Wired into the default `frob check` run (gate:registry
runs unconditionally), so a future silent gap in this file fails the
build via both the gate and this test.

No code changes to src/frob/vet/ were needed -- the unified registry
model and gate (src/frob/gates/_registry_exhaustiveness.py,
src/frob/registry/) already generically enforce this file; there is no
secrets-specific logic left to write.

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness::test_declared_total_is_3` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_secrets.py::TestExhaustivenessGateOverRealSecrets::test_no_secrets_violations` (pytest node id, verified passing when recorded)
