## Done report

Epic close: all five child tickets landed on main in series order.

- T-0667 (SYS-COV coverage totality, SYS103) -- landed prior to this
  wave, foundation this epic's remaining four tickets build on.
- T-0668 (exact interface conformance, SYS104) -- landed
  3a23e520631b89e58b232a18ae9cbc92b763ab4d.
- T-0669 (purpose contract, SYS105) -- landed
  1e8ad7bc87b9173d42a412c5fd4c538b358c6e84.
- T-0670 (binding totality + effect conformance, SYS106) -- landed
  3aafbf4f59f2f0db4059573c60f7daa9b66fbb3f.
- T-0671 (bounded/staleness-gated waiver mechanism, SYSWAIVE003 +
  un-droppable floor view) -- landed
  4e68b9bebdc001467fe3da043046fc89bdd3de78.
- T-0672 (N:M meta-test binding the structural-linter-adversarial-
  hardening.md denominator to the five checks) -- landed
  6b35c137aab92c1185f9c326ebf5aaa9f02488ab.

Each acceptance criterion below is bound to real evidence produced by
its own child ticket (not re-derived here):

- [0] COVERAGE TOTALITY -- SYS103 (T-0667): a FOREIGN file with any
  observed capability fires, on any root, not just `src/frob/`.
- [1] INTERFACE CONFORMANCE (exact) -- SYS104 (T-0668): a node's
  `interface=` attrs must equal its bound files' real public surface,
  both directions (undeclared export, declared-but-absent symbol).
- [2] PURPOSE CONTRACT -- SYS105 (T-0669): a node's `purpose=` profile
  bounds its allowed observed effect kinds; an effect outside the
  profile fires.
- [3] BINDING TOTALITY + EFFECT CONFORMANCE -- SYS106 (T-0670): a
  `FOREIGN` file reachable via resolved local imports from a bound
  node's own files, with an observed capability, fires -- laundering
  closed regardless of any scan-prefix restriction.
- [4] BOUNDED ESCAPE HATCHES + GATED CONFIG -- T-0671: SYS104/SYS105/
  SYS106 waivers are staleness-dated (`expires:YYYY-MM-DD` embedded in
  the mandatory `reason`), an expired/undated one re-fires its
  obligation plus a SYSWAIVE003 finding, and every active conformance
  waiver stays in the un-droppable floor view `sys_runner.py` already
  prints unconditionally every run.

EXHAUSTIVENESS DRIFT-LOCK (T-0343 mandate, epic body): T-0672's real-data
N:M meta-test (`tests/unit/strata/test_structural_linter_hardening_
totality.py`) binds `docs/design/structural-linter-adversarial-
hardening.md`'s full 23-entry corpus denominator to
`docs/design/registry/arch-checks.yaml`'s `SLH-*` catalogue -- both
totality directions (every denominator id dispositioned; no registry id
the denominator doesn't know about) -- and re-dispositions the five
`SLH-SYS-EVA-01..05` rows from a generic reasoned deferral to
`handled_by:SYS103/SYS100/SYS104/SYS105/SYS106`, addressed-by-check, with
matching `frob:enforces` directives closing REG008 for all five.

Disclosed scope cuts carried forward from child tickets (not
re-litigated here, each ticket's own Done report has the detail): SYS104/
SYS105 are opt-in per-node (a node must already declare `interface=`/
`purpose=` to be checked) since making them mandatory requires editing
`design/frob.strata`, which sat outside every child ticket's declared
scope. T-1113 (filed by T-0668) tracks that follow-up plus the
CHK-GATE-SYS104/105/106 `check-coverage.yaml` cross-reference gap (same
shape as SYS103/T-0667's own deferred registry gap).

Evidence: (5 acceptance criteria + 2 additional totality-mandate tests,
all --accepts-bound)
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103 (accepts 0)
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires (accepts 1)
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires (accepts 2)
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires (accepts 3)
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged (accepts 4)
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check

Filed: T-1113 (SYS104/SYS105 mandatory-declaration promotion +
CHK-GATE-SYS104/105/106 registry cross-reference, filed by T-0668).

Gates: each child ticket's own `frob check --ticket T-0XXX` ran clean
(chunked per playbook 3b) at land time; this epic-close pass re-verified
`tests/unit/strata/test_selfconform.py` and `tests/unit/strata/
test_structural_linter_hardening_totality.py` pass in full against the
merged main tip before writing this report.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_arch_checks_gate_reports_zero_unaccounted_slh_entries` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 7 error(s), 1851 warning(s), 424 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-strata/src/frob/vet/_supplychain.py:295
