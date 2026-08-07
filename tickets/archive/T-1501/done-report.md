## Done report

Land-repair for w17a-uxmisc (T-1218/T-1213). frob check --only coverage
--only sys was reporting 27 errors after ff31ae83's run_diagnosis split.

Fixed:
- COV005: the frob:doc/frob:tests/frob:waive AFFECT001 directives had
  silently ridden along from run_diagnosis onto the new private
  _assemble_doctor_report helper during the T-1501 split; moved them
  back onto run_diagnosis, the actual public caller.
- COV002 (6 findings): DoctorReport, _assemble_doctor_report,
  _combined_remediation, _log_doctor_diagnosis, run_diagnosis (all
  doctor.py) and NATIVE_AUTOREBUILD_DISABLE_ENV/_run_gates_bounded
  (gates/__init__.py, T-1213 residue) were changed with no open-ticket
  edge; bound all seven to this ticket.
- COV001: run_diagnosis itself now carries the
  docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
  frob:doc edge (moved from _assemble_doctor_report, see above).
- SELFAUDIT001 SYS100: tests/test_natives.py added to the testsuite
  node's fs.write capability list (sorted insertion) -- it does
  observed fs.write and had no declaration.
- SELFAUDIT001 SYS104 (x8): declared_min_frob_version and
  stale_binary_warning added to the cli node's interface=; the
  TestNativeAutorebuild class plus five T-1218 stale-binary-floor
  test functions added to the testsuite node's interface= -- all real,
  exercised public symbols with no prior declaration.
- design/frob.strata's cli and testsuite node interface= edits
  themselves needed an open-ticket edge (COV002); bound to this ticket
  since the prior T-1433/T-1267 edges on testsuite had both since
  closed.

frob check --only coverage --only sys: 0 errors (was 27), confirmed by
two full re-runs. git diff main --diff-filter=D --stat is empty.

### Changed
```
 design/frob.strata           |  14 ++-
 docs/modules/app.md          |  22 +++++
 docs/modules/gates.md        |  35 +++++++
 frob.lock                    |   2 +-
 src/frob/__main__.py         |   9 +-
 src/frob/app/_config_meta.py | 104 +++++++++++++++++++++
 src/frob/app/config.py       |   2 +
 src/frob/doctor.py           | 207 ++++++++++++++++++++++++----------------
 src/frob/gates/__init__.py   | 124 +++++++++++++++++++++++-
 tests/test_doctor.py         |  47 ++++++++++
 tests/test_natives.py        | 218 +++++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_config.py    |  35 +++++++
 tickets.md                   | 206 +++++++++++++++++++++++++++++++++++++++-
 13 files changed, 934 insertions(+), 91 deletions(-)
```

### Evidence
- `tests/test_doctor.py::test_run_diagnosis_reports_stale_binary_floor` (pytest node id, verified passing when recorded)
- `tests/test_doctor.py::test_run_diagnosis_stale_binary_none_when_no_floor` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor` (pytest node id, verified passing when recorded)
- `tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_env_var_skips_autorebuild` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 223 warning(s), 762 waived
- error-findings: PRE001@tickets/T-1501, WIRE001@tests/test_natives.py
