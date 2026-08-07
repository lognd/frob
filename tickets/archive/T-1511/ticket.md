---
id: T-1511
title: WIRE001 on _FakeCompletedProcess test-fixture stand-in (check native/ts runner
  tests)
state: done
kind: docs
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_check_native_cargo_runners.py
- tests/unit/test_check_ts_runners.py
- tests/unit/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/conftest.py
  reason: promoting the duplicated _FakeCompletedProcess stand-in (now confirmed used
    by 2 files) to a shared tests/unit conftest per the ticket's own follow-up criterion
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_success_parses_cargo_json
- tests/unit/test_check_ts_runners.py::TestRunTscRealPaths::test_success_parses_clean_output
designated_repro_test: null
threat: null
component: null
---
WIRE001 flags _FakeCompletedProcess in tests/unit/test_check_native_cargo_runners.py
and tests/unit/test_check_ts_runners.py as unreached outside its own tests. It is a
private per-file test-fixture stand-in used only by each file's own tests below --
there is no production caller to wire it to by design, it exists solely as a
subprocess.CompletedProcess-shaped stub for monkeypatched guarded_subprocess_run
returns, mirroring the tests/unit/test_conftest_stackdump.py::_load_conftest (T-1466)
precedent. Follow-up: evaluate whether this stub should move to a shared
test-support module (frob.testing or a conftest fixture) if more runner tests want
the same stub, or whether the current per-file scope is intentionally final (in
which case this ticket should close as won't-fix with that recorded).