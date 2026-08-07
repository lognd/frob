## Done report

Root cause: `design/frob.strata` itself was never wrong -- T-0864 (`frob
natives build`) added the `natives` node (`may "exec"`, its own
`assume "weakness:CWE-78:natives"` discharge directive, and its
`f_cli_natives`/`f_natives_core` flows) correctly and completely, but
three test files that hardcode a running count/set of the model's
node/flow/claim surface were never re-measured against it -- the same
"docstring narrates a delta, nobody re-derives the running total"
drift class the T-0707/T-0440 comments already call out by name in this
same test file. `tests/system/test_frob_self_model.py` asserted
15 nodes/42 flows/26 claims and an `assumed_ids` set missing
`weakness:CWE-78:natives`; the real elaborated model has 16/44/27. Same
root cause, same T-0864 blind spot, hit `tests/unit/strata/
test_export_golden.py`'s three committed golden exports
(`tests/golden/frob_export_{k8s.yaml,seccomp.json,iam.json}`), which
were byte-for-byte generated against the pre-`natives` model and never
regenerated. No claim REFUTEs and no `frob check --only sys` violation
exists against the live model -- this was purely test/golden drift, not
a prover weakening or a real regression, so no waiver was needed and
none was added.

Changed:
- tests/system/test_frob_self_model.py::TestFrobSelfModel.test_parses_and_elaborates
  (node/flow/claim counts 15/42/26 -> 16/44/27, docstring updated)
- tests/system/test_frob_self_model.py::TestFrobSelfModel.test_every_claim_proves
  (claim_results count 26 -> 27, `assumed_ids` gains
  `weakness:CWE-78:natives`, docstring updated)
- tests/system/test_frob_self_model.py (added missing TEST001
  `frob:tests design/frob.strata::frob.f_cli_natives` /
  `frob.f_natives_core` directives -- these two T-0864 flows had no
  bound unit test either, same drift)
- tests/golden/frob_export_k8s.yaml (regenerated via
  `frob.strata._export.export_k8s_netpol` against current
  `design/frob.strata`)
- tests/golden/frob_export_seccomp.json (regenerated via
  `frob.strata._export.export_seccomp`)
- tests/golden/frob_export_iam.json (regenerated via
  `frob.strata._export.export_iam`)

Evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves -- PASS
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates -- PASS
- tests/system/test_frob_self_model.py (full module, 4 tests) -- PASS
- tests/unit/strata/test_export_golden.py::TestExportGolden::{test_k8s,test_seccomp,test_iam} -- PASS (were FAILED before this ticket)
- tests/unit/strata/ (full dir) + tests/system/test_frob_self_model.py -- all PASS

Filed: none -- the two drift sites (self-model test, golden exports)
are the complete blast radius; scope-added `tests/unit/strata/
test_export_golden.py` + `tests/golden/**` to this ticket rather than
filing separately since it is the identical T-0864 drift, not a
distinct problem.

Gates: `frob check --ticket T-0967 --only gates-fast` clean,
`--only gates-native` clean, `--only gates-security` clean,
`--only static` clean. `--only lint` shows 3 pre-existing ruff-format
warnings in unrelated files (src/frob/arch/_lock_ordering.py,
tests/test_ticket_land.py, tests/unit/test_arch.py) -- outside this
ticket's scope, not touched, not introduced by this change.

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 5105 warning(s), 220 waived
- error-findings: none (measured, zero errors)
