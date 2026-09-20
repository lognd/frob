## Done report

Changed:
src/frob/gates/_tickets_gate.py::_utc_today (frob:tests directive repointed)
docs/modules/gates.md (TICK004 row: severity computed via _utc_today() seam)

Evidence:
tests/test_tickets_priority.py::TestTick004QueueRot::test_severity_is_utc_deterministic_across_local_timezones
cmd:uv run frob check --only drift exit=0 sha256=d13ef50e957c

Filed: none

Gates: frob check --only drift clean (0 errors, DRIFT002 resolved); frob check --ticket T-4399 clean for in-scope files (gate:FMT/gate:PRE now pass; remaining FAILs -- gate:DOC T-4400 phantom-ticket citation, gate:LARGE, gate:TICK TICK004/TICK006 backlog, ruff-format on src/frob/gates/__init__.py -- are repo-wide pre-existing findings unrelated to this ticket's files, per the --ticket scope-note)

### Changed
```
 docs/modules/gates.md           | 2 +-
 src/frob/gates/_tickets_gate.py | 3 ++-
 tickets/T-4399/ticket.md        | 3 +++
 3 files changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_severity_is_utc_deterministic_across_local_timezones` (pytest node id, verified passing when recorded)
- `cmd:uv run frob check --only drift exit=0 sha256=d13ef50e957c` (cmd evidence, exit=0)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 4953 warning(s), 960 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, TICK004@tickets.md, TICK006@tickets.md
