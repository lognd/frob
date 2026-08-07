## Done report

Changed:
- tests/unit/strata/test_structural_linter_hardening_totality.py (new file: 6 tests, real-data N:M meta-test)
- docs/design/registry/arch-checks.yaml (SLH-SYS-EVA-01..05 re-dispositioned from generic out_of_scope:none to handled_by:SYS103/SYS100/SYS104/SYS105/SYS106)
- src/frob/strata/_selfconform.py::check_self_conformance (added 5 frob:enforces SLH-SYS-EVA-* directives)
- docs/modules/strata.md (Hardening-doc denominator totality section)

T-0672 is T-0341's close condition: binds `docs/design/structural-linter-
adversarial-hardening.md`'s full corpus denominator (23 entries: 5
principles + 9 arch-evasion + 9 strata-evasion rows, all already minted
stable SLH-* ids in `arch-checks.yaml` by T-0391) to the five conformance
checks T-0667-T-0670 built. Two parts:

1. A real-data N:M meta-test (`test_structural_linter_hardening_
   totality.py`), same posture as the sibling `test_registry_
   reconciliation_*.py` pin tests (T-0384-T-0392): hardcodes the corpus
   denominator and asserts (a) every denominator id resolves to a real
   registry entry, (b) every one carries a real disposition (never
   UNDISPOSITIONED), (c) the registry has no SLH-* id the denominator
   does not know about (both totality directions), and (d) `frob
   registry audit`'s own `audit_registry_file.exhausted` agrees --
   proving this via the SAME accounting the live `frob check --only
   registry` gate uses, not a parallel count.
2. Re-dispositioning: the 5 SLH-SYS-EVA rows this epic's checks
   literally answer (unmodeled module -> SYS103, under-declared
   capability -> SYS100, undeclared public surface -> SYS104, purpose
   drift -> SYS105, binding laundering -> SYS106) are moved from a
   generic "design-defense, not itself checkable" reasoned deferral to
   `handled_by:<real rule>` -- addressed-by-check, verified directly
   against the registry's raw disposition string and against
   `known_gate_rule_ids()` (never assumed). Matching `frob:enforces`
   directives on `check_self_conformance` close REG008 for all five.
   The other 18 denominator rows (5 principles + 9 arch-evasion + 4
   remaining strata-evasion rows) are LEFT as their existing honest
   reasoned deferrals -- they motivate gate design holistically (no
   single bindable rule), forcing a `handled_by:` there would be a false
   claim.

Evidence:
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned (acceptance [0])
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries (acceptance [1] -- the drift-detection direction: a new undispositioned corpus entry would flip `exhausted` false)
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_has_a_real_registry_entry
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_registry_has_no_extra_slh_entries_beyond_denominator
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_bound_rules_are_real_known_gate_rules

Filed: none new (the CHK-GATE-SYS104/105/106 check-coverage.yaml
cross-reference gap T-1113 already covers is the only remaining
registry-side follow-up touching this area).

Gates: `uv run frob check --ticket T-0672` clean across prework/static/
registry/gates-native/gates-security/test/coverage/tickets/doclink/
docanchor (chunked per playbook 3b). `registry` group's REG008 for the
five SLH-SYS-EVA-* entries is now RESOLVED by this ticket's own
`frob:enforces` directives (measured before/after: 5 REG008 warnings ->
0). `lint` shows pre-existing ruff-check/format debt in files outside
this ticket's scope (confirmed present on bare `main` root, unrelated,
same set noted in T-0670/T-0671's Done reports). `coverage` shows one
pre-existing COV001 (`src/frob/gates/_tracked_files.py::tracked_files`),
also confirmed present on bare `main` root, unrelated.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_has_a_real_registry_entry` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_registry_has_no_extra_slh_entries_beyond_denominator` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_bound_rules_are_real_known_gate_rules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 7 error(s), 1051 warning(s), 426 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:295, PRE001@tickets/T-0672
