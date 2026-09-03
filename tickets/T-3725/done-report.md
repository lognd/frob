## Done report

Root cause: `_doctor_healthy` in src/frob/doctor.py hard-failed (exit 1)
whenever `scaffold_needs_apply` was non-empty -- CI checkouts never run
`frob scaffold apply`, so missing/stale LOCAL git hooks (.git/hooks/
pre-commit and friends, T-0736) always fired there, even with a clean
suite and a clean self-gate (CI run 33715737237). Separately,
doctor_runner.py's plain renderer printed the fixed label "native
extensions missing" whenever ANY health check failed, misleadingly
blaming extensions even when frob_core/strata_core both reported
available=True (their "version=unknown" is just an unset __version__
attribute -- `_extension_status` already treats available=True as
healthy regardless of version string, so there was no real
misclassification bug there, just a misleading label).

Fix: (1) removed scaffold_needs_apply from `_doctor_healthy`'s
conditions -- it is now informational only, matching how `drift` and a
CONFIRMED-dead `live_land_process` are already informational-only; it
still surfaces in `remediation` and via a new `_print_scaffold_
disclosure` helper on the otherwise-healthy plain-text path (mirrors
`_print_orphaned_land_lock_disclosure`'s existing pattern). (2) fixed
`_run_plain`'s unhealthy-branch label (extracted into
`_print_unhealthy_summary` to stay under ARCH103) to name the actually-
unavailable extensions, or a neutral "frob doctor found issue(s)"
heading when the failure is unrelated to extensions.

Did not touch .github/workflows/ci.yml -- the doctor fix alone resolves
the failing step; no workflow change was needed.

Tests updated/added: tests/system/test_cli_doctor.py::
TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_
scaffold_blocks_missing (kept the original test id so pre-existing
frob:tests evidence citations elsewhere still resolve; assertions now
require healthy=True while remediation still names the hooks fix).
tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerScaffoldDisclosure
(new): disclosure-line-present and disclosure-line-absent cases for
`_print_scaffold_disclosure`.

Verification: `frob check --ticket T-3725` clean except pre-existing
repo-wide gate:DEPR DEPR006 (deprecated-baseline lock producer stale),
confirmed present and unrelated on unmodified main HEAD edf076409.
`frob test --base main` ran the 28-test touched set, exit=0.

### Changed
```
 tickets/T-3725/done-report.md | 56 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3725/ticket.md      | 14 ++++++++++-
 2 files changed, 69 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerScaffoldDisclosure::test_healthy_report_with_scaffold_needs_apply_prints_disclosure_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerScaffoldDisclosure::test_healthy_report_with_no_scaffold_blocks_prints_nothing_extra` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy::test_unhealthy_plain_exits_1_and_prints_remediation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 4307 warning(s), 924 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
