## Done report

Added `frob.app._config_meta.stale_binary_warning` (plus
`declared_min_frob_version` and `_parse_version_tuple` helpers): a
version-ordering check (not the exact-match `stale_install_warning`
already in this module) against a repo's own `frob.toml`
`min_frob_version` floor. Fires for ANY repo declaring the key, not just
frob's own checkout -- the exact gap the 2026-08-02 stale-merge-driver
incident exposed.

Wired in two places:
- `frob.__main__._dispatch` prints the warning to stderr on every CLI
  invocation, right alongside the existing `stale_install_warning` print.
- `frob.doctor.run_diagnosis` gained `DoctorReport.stale_binary` (str |
  None); a non-None value makes `healthy` False and folds into
  `remediation`, same class as `venv_shims`/`stale_ticket_leases`.

Docs: docs/modules/app.md's Entry point section documents both checks
side by side (exact-match vs floor, when each fires).

Scope was extended (frob ticket scope --add, reasons recorded) to cover
src/frob/app/_config_meta.py (where stale_install_warning already lived --
the natural home for this sibling check) and tests/unit/test_config.py
(its existing test module), plus frob.lock (touched by the frob ack this
ticket's DRIFT001 fix required).

### Changed
```
 tickets.md | 39 ++++++++++++++++++++++++++++++++++++---
 1 file changed, 36 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_doctor.py::test_run_diagnosis_reports_stale_binary_floor` (pytest node id, verified passing when recorded)
- `tests/test_doctor.py::test_run_diagnosis_stale_binary_none_when_no_floor` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_binary_warning_none_when_no_floor_declared` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_binary_warning_none_when_version_meets_floor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 288 warning(s), 747 waived
- error-findings: ARCH001@src/frob/doctor.py, PII012@tests/test_doctor.py, SELFAUDIT001@design
