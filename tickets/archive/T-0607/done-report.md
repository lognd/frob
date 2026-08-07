## Done report

## Done report

Changed:
- src/frob/strata/_compliance.py::CMPL_REGISTRY_UNIT_IDS
- src/frob/strata/_compliance.py::check_cmpl_registry_unit_dispositions
- src/frob/strata/_compliance.py::check_cmpl_registry
- src/frob/strata/_compliance.py::_cmpl_disposition_violation
- docs/design/registry/compliance.yaml (17 CMPL-* entries: deferred:T-0607 -> reasoned out_of_scope)
- tests/unit/strata/test_compliance.py::TestCmplRegistry (new)
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness (updated for the new zero-deferred state, one new test added)

Real enforcement, not just catalog prose: `check_cmpl_registry_unit_dispositions`
(rule COMPLIANCE005) refuses any of the 17 CMPL_REGISTRY_UNIT_IDS entries
sitting in a `deferred:*`/undispositioned disposition state ever again --
the exact T-0388/T-0607 self-reference regression this ticket closes.
`check_cmpl_registry` is the real-file entrypoint (loads compliance.yaml
via the shared `frob.registry.load_registry_dir`). Both are pure/typed,
consume real `RegistryEntry` data, and are proven with fixtures: a
`deferred:`/undispositioned fixture fails (test_deferred_disposition_is_refused,
test_undispositioned_is_refused), a `handled_by:`/`out_of_scope:` fixture
passes clean (test_handled_by_and_out_of_scope_dispositions_pass), plus
real-file load-success/load-failure and id-not-tracked/id-absent edge
cases. tests/test_registry_reconciliation_compliance.py additionally pins
this against the REAL compliance.yaml (test_cmpl_registry_units_carry_handled_by_or_out_of_scope)
and updates the now-obsolete positive `deferred:` fixture test to assert
the new zero-deferred state instead of requiring a fixture that no longer
exists.

Disposition choice: all 17 entries flip to `out_of_scope:<reason>` rather
than `handled_by:<rule>`, because `handled_by` is validated by
`frob.gates._registry_exhaustiveness.registry_gate` against the live
`_KNOWN_GATE_RULES | policy-rule-ids` union (src/frob/gates/__init__.py),
which is out of this ticket's declared scope to extend -- using
`handled_by:COMPLIANCE005` would immediately fail REG002 (dangling
enforcement reference) since COMPLIANCE005 is not (yet) a registered gate
rule id. The `out_of_scope` reason is honest and reasoned: per
docs/design/compliance-corpus.md's own research-method note, primary-
source leaf-control text for these 17 frameworks (SOC2, PCI-DSS, ISO
27002, CIS, ASVS, FedRAMP, NIST, SLSA, frob's own catalog) is
partial/paywalled/unverified -- per-control static enforcement cannot be
built without fabricating unverified control text. The standing
structural compensating control (never silently reverting to
deferred/undispositioned again) is COMPLIANCE005, named in each entry's
disposition text.

Follow-up filed (out of this ticket's file-scope, not silently folded
in): wiring `check_cmpl_registry`/COMPLIANCE005 into `frob check`'s live
gate run (touching src/frob/gates/__init__.py and/or
src/frob/strata/_audit.py, both outside T-0607's declared scope) and
registering COMPLIANCE005 as a known gate/policy rule id so a future
ticket CAN flip these entries to `handled_by:COMPLIANCE005` for real
cross-validated enforcement rather than `out_of_scope`. See T-0607's
Done report ticket-id note below.

Evidence: 11 pytest node ids bound to acceptance[0] via `frob ticket
evidence T-0607 ... --accepts 0`:
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_undispositioned_is_refused
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_handled_by_and_out_of_scope_dispositions_pass
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_outside_the_universe_is_ignored
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_absent_from_entries_is_silently_skipped
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_missing_file_is_parse_failed
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_cmpl_registry_units_carry_handled_by_or_out_of_scope
- tests/test_registry_reconciliation_compliance.py::TestExhaustivenessGateOverRealCompliance::test_no_compliance_violations

Filed: none (no out-of-scope bug found needing a new ticket during this
pass; the deferred registry-gate-wiring follow-up above is a design
extension, not a bug -- if the coordinator wants it tracked as a ticket
rather than left as a Done-report note, flag it and one will be filed).

Gates: `uv run frob check --ticket T-0607 --only lint` clean (0/0).
`uv run frob check --ticket T-0607 --only static` clean for
frob-exports warnings only (pre-existing repo-wide pattern, not new).
`uv run frob check --ticket T-0607 --only gates-fast` (run twice,
foreground, full ~35s each): COV/DOC/DRIFT/PRE/SCOPE all clean after
fixing directive syntax (`Class.method` not `Class::method`) and adding
a real `#anchor` to the two new `frob:doc` targets. Remaining
gates-fast FAILs (REL001 minor-API-bump-needed, TEST002/TEST006/TEST010
on src/frob/perf/_collectors.py, src/frob/vet/_capability_modes.py,
tests/system/test_spawn_budget.py, tests/test_perf_loop_invariant_effect_lock.py,
.frob/coverage-stamp) are pre-existing repo-wide state from unrelated
in-flight tickets, not touched by this ticket's scope -- confirmed via
grep, zero hits for "compliance" in the gates-fast error list.
`uv run frob test --base main` (touched-set): PASS, exit=0.
Deviation: gates-fast's own subprocess invocations of `uv run` repeatedly
resynced `uv.lock`'s frob version line to match a locally-newer
pyproject.toml version bumped by a concurrent sibling worktree's land
(the "PRE001/SCOPE001 artifact" a recent main commit already tried to
fix); reverted with `git checkout -- uv.lock` after every check run per
the playbook's land-owned-files rule -- never committed.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_undispositioned_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_handled_by_and_out_of_scope_dispositions_pass` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_outside_the_universe_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_absent_from_entries_is_silently_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_missing_file_is_parse_failed` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_cmpl_registry_units_carry_handled_by_or_out_of_scope` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_compliance.py::TestExhaustivenessGateOverRealCompliance::test_no_compliance_violations` (pytest node id, verified passing when recorded)
