## Done report

Changed: docs/modules/deploy.md (windows-generation bullet list, Scope and honesty notes section)
Evidence: tests/unit/deploy/test_generate_windows.py::TestInstall.test_creates_service_when_bin_path_declared, ::test_service_not_present_notes_missing_bin_path, ::test_bin_path_args_optional (20/20 passing, pytest -q)
Filed: none
Gates: frob check --ticket T-0941 clean (0 errors, gate:PRE cleared after re-sweep post scope-add)

### Changed
(no changed files detected)

### Evidence
- `tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_without_args` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4150 warning(s), 219 waived
- error-findings: none (measured, zero errors)
