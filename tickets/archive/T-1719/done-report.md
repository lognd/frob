## Done report

Implemented item 3 of T-1719's plan only: `frob doctor` (src/frob/doctor.py)
now measures the on-PATH global `frob --version` against this
invocation's own version and reports the comparison as
`DoctorReport.global_binary` (a new `GlobalBinarySkew` model:
global_version/local_version/skewed). A measured disagreement makes
`healthy=False` and folds a remediation line naming both versions and the
reconcile command into `DoctorReport.remediation`, mirroring the
`.claude/hooks/frob-suggest.py` `frob-version-skew` nudge's own
spawn-strip-compare measurement (that hook already existed and covers the
interactive-command case; this is the same check surfaced through
`frob doctor` for a non-interactive/scripted caller). An unmeasurable
comparison (no global `frob` on PATH) never counts as skew.

Items 1 and 2 of T-1719's plan (fold `sync-claude-config.py` into a real
frob verb; gate the resulting drift in `frob check`) were NOT implemented
and are disclosed as cut, not silently dropped:

- Implementing the sync verb needs a new top-level subcommand wired
  through src/frob/app/app.py's `_RUNNER_MODULE_NAMES`/
  `_SUBCOMMAND_RUNNER_NAMES`/`_import_runner_module`, src/frob/app/
  config.py's `Subcommand` enum, and a new runner module -- all outside
  this ticket's narrowed scope (doctor.py/cli.md/test_doctor.py only,
  narrowed deliberately to avoid a broad lease blocking the fleet).
- Gating the drift needs `_KNOWN_GATE_RULES`/docs/modules/gates.md, both
  explicitly off-limits during this dispatch (held by other concurrent
  agents on T-1773/T-1735/T-1781), and logically depends on the sync verb
  existing first.

Filed as follow-ups (drafts, real ids assigned at land):
- T-1808: fold sync-claude-config.py into a frob verb.
- T-1809: gate the resulting drift once the verb exists.

Changed:
- src/frob/doctor.py::GlobalBinarySkew (new)
- src/frob/doctor.py::global_binary_skew (new)
- src/frob/doctor.py::_probe_global_frob_version (new, private)
- src/frob/doctor.py::_global_binary_skew_remediation (new, private)
- src/frob/doctor.py::DoctorReport (new global_binary field)
- src/frob/doctor.py::_combined_remediation/_collect_doctor_scans callers,
  _log_doctor_diagnosis, _assemble_doctor_report, run_diagnosis (threaded
  the new check through)
- docs/modules/cli.md (new section: frob doctor: global-vs-local frob
  binary skew (T-1719))

Evidence:
- tests/test_doctor.py::test_global_binary_skew_reports_disagreement
- tests/test_doctor.py::test_global_binary_skew_none_when_no_global_frob
- tests/test_doctor.py::test_global_binary_skew_not_skewed_when_versions_agree
- tests/test_doctor.py::test_run_diagnosis_unhealthy_on_global_binary_skew
- 13/13 tests/test_doctor.py pass (uv run pytest tests/test_doctor.py -q)

Gates: `uv run frob check --ticket T-1719` exit 0, all gate:* families
pass (ruff-check/ruff-format failures present are pre-existing repo-wide
debt in files this ticket never touched -- doctor.py/test_doctor.py/
cli.md are clean under both). `uv run frob check --land-parity` reports
clean (0 unscoped errors).

### Changed
```
 docs/modules/cli.md                |  33 +++++++++
 frob.lock                          |  20 +++++-
 src/frob/doctor.py                 | 139 ++++++++++++++++++++++++++++++++++---
 tests/test_doctor.py               |  81 +++++++++++++++++++++
 tickets/T-1719/ticket.md           |  37 +++++++++-
 tickets/T-1808/ticket.md |  49 +++++++++++++
 tickets/T-1809/ticket.md |  35 ++++++++++
 7 files changed, 381 insertions(+), 13 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 612 warning(s), 734 waived
- error-findings: none (measured, zero errors)
