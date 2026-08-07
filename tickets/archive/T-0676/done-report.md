## Done report

Recount method: parsed the DENOMINATOR MANIFEST's `entries:` yaml block in
docs/design/supply-chain-corpus.md with a small script (grep + a python
verification pass) that extracted every `- {id: ..., class: [...],
checkability: [...]}` line, counted unique ids, and independently tallied
class/checkability/sourcing distributions. Cross-checked by hand against the
prose (16 attack sections 1.1-1.16, 9 defense sections 2.1-2.9, 16 detection
rows D1-D16 in the section-3 table = 41 catalogued controls total, matching
the registry.yaml file's own `total: 41`).

Result: 41 unique entries confirmed, no duplicates. The doc's own `TOTAL: 39`
was wrong; corrected to 41. All downstream subtotals that summed from that
same entries list were also drifted and are now corrected:
- totals_by_class: attack=16, defense=9, detection=19 (three ids carry a dual
  class tag: attack-native-extension-opacity, defense-openssf-scorecard,
  defense-osv -- corrected the doc's own dual-tag count note from 2 to 3)
- totals_by_checkability: statically-detectable_only=11 (was 8),
  requires-external-data_only=16 (was 15), mixed_static_and_external=9
  (unchanged), process-only=2 (unchanged), advisory_component=3 (was 4)
- sourcing_honesty: fully_primary_sourced=38 (was 36), partial_flagged=3
  (unchanged, same 3 ids)
- frob_vet_reconciliation: reclassified all 41 entries by their own
  frob.vet-mapping prose (IMPLEMENTED / PARTIAL / NOT implemented / out of
  scope) -- implemented=11, partial=5, not_implemented_gap=19,
  out_of_scope_by_design=6 (previously summed to only 39, i.e. 2 entries
  were silently missing from this breakdown too)

docs/design/registry/supply-chain.yaml already had the correct 41 entries
and `total: 41` (landed under T-0389); only its explanatory comment noting
the doc/registry mismatch needed updating now that the mismatch is fixed.

Changed:
docs/design/supply-chain-corpus.md::denominator_manifest (TOTAL and all
subtotal fields)
docs/design/registry/supply-chain.yaml (mismatch-note comment only, no
entry/total change)

Evidence:
tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41
tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted
(both bound to acceptance[0]; ran `uv run pytest
tests/test_registry_reconciliation_supply_chain.py -q` -- 8 passed, 0
failed)

Filed: none

`uv run frob test --base main` (full run, exit 429s python/11.89s strata):
FAILs almost entirely native/environment artifacts unrelated to this
ticket's scope -- `sys audit proved=False`, `test_doctor` natives-
present/absent, `test_cli_native_missing`, `test_frob_self_model`, CLI
check-stage tests -- matching the known worktree-natives-artifact class
(fresh worktree strata_core/frob_core builds), not a regression from this
change. Confirmed via `git diff main --stat`: this ticket's diff touches
only docs/design/registry/supply-chain.yaml, docs/design/supply-chain-corpus.md,
and tickets.md -- zero Python/Rust/strata source -- so none of frob test's
python/rust/strata suites are actually in this ticket's touched set;
its failures pre-date and are independent of this change. The bound
evidence above (targeted pytest run of the actual reconciliation test
file) is the real touched-set verification for this doc-only ticket.

Gates: `uv run frob check --ticket T-0676 --only lint` clean (0/0).
`uv run frob check --ticket T-0676 --only static` 0 errors (124
pre-existing warnings, none touching this ticket's scope).
`uv run frob check --ticket T-0676 --only gates-native` 0 errors (all
warnings pre-existing/waived).
`uv run frob check --ticket T-0676 --only gates-fast` gate:REG passes (0
errors, 2 pre-existing warnings). Two other gates in this stage-group
(gate:PRE stale-sweep, gate:SCOPE uv.lock) were transient/unrelated:
PRE001 cleared by re-running `frob ticket sweep T-0676`; the uv.lock drift
came from `make core`'s cargo/uv build touching the version line and was
reverted (`git checkout -- uv.lock`), per the land-owned-files rule --
never part of this ticket's own change. gate:TEST's 2 unwaived errors
(TEST010 on tests/test_perf_loop_invariant_effect_lock.py and
tests/system/test_spawn_budget.py) are pre-existing and outside this
ticket's scope.

### Changed
```
 docs/design/registry/supply-chain.yaml |  6 ++-
 docs/design/supply-chain-corpus.md     | 27 ++++++------
 tickets.md                             | 80 ++++++++++++++++++++++++++++++++--
 3 files changed, 95 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
