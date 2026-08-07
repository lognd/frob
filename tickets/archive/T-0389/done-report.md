## Done report

Reconciled docs/design/registry/supply-chain.yaml (41 entries) against
actual enforcement. 39 entries carried disposition deferred:T-0389 (a
self-deferral -- T-0389 is this review-gated reconciliation ticket and
would orphan the deferral the moment it closes); re-pointed all 39 to a
newly filed standing ticket, T-0721 (ex-draft, id lost at land) (implement checkable-control
enforcement for SC-* supply-chain registry entries), scoped to
src/frob/vet/**. The remaining 2 entries (SC-ATTACK-TRANSITIVE-BLINDNESS,
SC-DEFENSE-CAPABILITY-SANDBOXING) were already honestly dispositioned
out_of_scope(process-only) before this pass and were left untouched.
Disposition sum: 39 deferred + 2 out_of_scope = 41 == declared total.

Added tests/test_registry_reconciliation_supply_chain.py (8 tests)
mirroring the T-0384/T-0385/T-0386/T-0387/T-0388 pin-test precedent:
registry-file loads/no-malformed, declared total == 41, audit exhausted
with disposition sum == total, every deferred entry resolves dynamically
to a real non-done ticket in the live queue, no entry defers to T-0389
itself (regression lock), and registry_gate raises zero violations for
supply-chain.yaml specifically. Added the new test file to T-0389's scope
via `frob ticket scope --add` before recording evidence.

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestExhaustivenessGateOverRealSupplyChain::test_no_supply_chain_violations` (pytest node id, verified passing when recorded)
