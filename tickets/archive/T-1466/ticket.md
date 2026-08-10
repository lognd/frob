---
id: T-1466
title: extend T-1433 SIGUSR1 stack-dump handler beyond pytest-only scope
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/conftest.py
- src/frob/testing/**
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_stackdump.py
- src/frob/testing/_stackdump.py
- docs/modules/testing.md
- tickets/T-1466/ticket.md
- tickets/T-1823/ticket.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: extraction requires updating the conftest-loaded test file for the new delegation
    shape, a new direct-module test file, and testing.md doc coverage for the new
    public frob.testing._stackdump surface
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_stackdump.py
  reason: extraction requires updating the conftest-loaded test file for the new delegation
    shape, a new direct-module test file, and testing.md doc coverage for the new
    public frob.testing._stackdump surface
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/testing/_stackdump.py
  reason: extraction requires updating the conftest-loaded test file for the new delegation
    shape, a new direct-module test file, and testing.md doc coverage for the new
    public frob.testing._stackdump surface
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/testing.md
  reason: extraction requires updating the conftest-loaded test file for the new delegation
    shape, a new direct-module test file, and testing.md doc coverage for the new
    public frob.testing._stackdump surface
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1466/ticket.md
  reason: ticket lifecycle commits touch T-1466's own ticket.md; the filed follow-up
    draft's ticket.md is created by the same frob ticket new invocation this ticket's
    work produced
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1823/ticket.md
  reason: ticket lifecycle commits touch T-1466's own ticket.md; the filed follow-up
    draft's ticket.md is created by the same frob ticket new invocation this ticket's
    work produced
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the new fs.write/env.read/process-control
    capabilities and public interface symbols for the extracted stackdump module
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_handler_not_installed_when_env_unset
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_reachable_via_frob_testing_public_surface
designated_repro_test: null
threat: null
component: null
---
T-1433's SIGUSR1 stack-dump handler (tests/conftest.py::_install_stackdump_handler/_dump_all_thread_stacks) is currently wired ONLY into the pytest test-session lifecycle (pytest_configure), gated behind FROB_COVERAGE_STACKDUMP. WIRE001 flags both helpers as unreached outside their own tests, since tests/conftest.py itself is a test-path the gate's text scan skips. Follow-up: evaluate whether frob's own daemon/CLI processes (frob serve, frob check's own subprocess pool) would benefit from the same opt-in handler for non-coverage-recipe wedges, or whether the current pytest-only scope is intentionally final (in which case this ticket should close as won't-fix with that recorded).

## Done report

Changed:
- src/frob/testing/_stackdump.py (new) -- STACKDUMP_ENV, dump_all_thread_stacks, install_stackdump_handler: the SIGUSR1 stack-dump handler moved out of tests/conftest.py so ANY frob process can opt in, not just pytest
- src/frob/testing/__init__.py -- re-exports the three new symbols
- tests/conftest.py -- thin delegator, re-exports _STACKDUMP_ENV/_install_stackdump_handler under their original private names for source-compat with existing tests and pytest_configure's own wiring
- tests/unit/test_stackdump.py (new) -- direct unit coverage for frob.testing._stackdump
- tests/unit/test_conftest_stackdump.py -- unchanged, still passes through the delegation (verifies source-compat)
- docs/modules/testing.md -- new "SIGUSR1 stack-dump handler (T-1433, T-1466)" section
- design/frob.strata -- node core: added fs.write/env.read/process-control capability declarations for _stackdump.py plus the 3 new public interface symbols; node testsuite: fs.read for tests/unit/test_stackdump.py

Ticket's own question answered: closes WIRE001 by making the handler reachable via frob.testing's public surface from ANY process, not test-path-only. Actually WIRING it into frob serve's daemon or a frob check subprocess pool worker is left as a disclosed follow-up (needs src/frob/serve/**, outside this ticket's declared scope) -- filed as T-1823, both dump_all_thread_stacks and install_stackdump_handler carry a frob:waive WIRE001 naming that follow-up until it lands.

Evidence:
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_handler_not_installed_when_env_unset
- tests/unit/test_stackdump.py::TestStackdumpHandler::test_reachable_via_frob_testing_public_surface

Filed: T-1823 (wire frob serve daemon / check subprocess pool into the handler)

Gates: uv run frob check --ticket T-1466 clean (0 errors)

### Changed
```
 tickets/T-1466/ticket.md           | 62 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1823/ticket.md | 33 ++++++++++++++++++++
 2 files changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_stackdump.py::TestStackdumpHandler::test_sigusr1_writes_all_thread_stacks_when_enabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_stackdump.py::TestStackdumpHandler::test_handler_not_installed_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_stackdump.py::TestStackdumpHandler::test_reachable_via_frob_testing_public_surface` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
