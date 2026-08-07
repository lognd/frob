## Done report

T-0720 asked for pytest.mark.timeout overrides on slow tests/system/**
tests plus an audit of the rest of tests/system/** for anything else that
might exceed the 120s global default (T-0692).

Audit performed this pass:
- Only two files carry pytestmark = pytest.mark.slow in tests/system/**:
  test_scaffold_dx.py and test_natives_build_integration.py. Both already
  carry an explicit @pytest.mark.timeout override (300 and 180
  respectively), added by earlier tickets (T-0742/T-0996 for
  test_scaffold_dx.py, T-0993 for test_natives_build_integration.py), each
  with an observed-runtime justification comment already in place.
- Timed both directly this pass to confirm the existing overrides still
  hold generous (>3x) headroom under current load:
  test_scaffold_dx.py (both slow tests): ~5s wall.
  test_natives_build_integration.py: ~9s wall.
  Both existing overrides (300s / 180s) give more than 3x headroom over
  these freshly observed runtimes, satisfying this ticket's wall-time
  margin requirement without any value change.
- Grepped every other tests/system/**/*.py file for subprocess.run/uv
  sync/Popen usage not already carrying pytest.mark.slow or
  pytest.mark.timeout. The remaining files spawn only short-lived git
  init/CLI subprocess calls or use fake/injected build functions
  (test_scaffold_pool.py's `_fake_build_ok`), not the real
  minutes-class build path -- none of them need an override.
- Ran the full non-slow tests/system/** suite (`-m "not slow"`): 1m21s
  wall for the whole parallel run, no individual test over the 120s
  default. One unrelated pre-existing failure
  (test_system.py::test_sys_audit_hardened_waived_two_user_model_proved)
  reproduces identically on main HEAD, outside this ticket's scope --
  left untouched.

Net: this ticket's acceptance is already satisfied by prior tickets'
work; this pass is a confirming audit with no source changes needed. No
code diff to report.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error` (pytest node id, verified passing when recorded)
- `tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 1888 warning(s), 381 waived
- error-findings: PII012@src/frob/tickets/_leases.py
