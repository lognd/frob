## Done report

Added SYS110 to docs/modules/gates.md's frob:enumerates member list,
restoring the unscoped floor (DOCENUM001 0 -> 1 regression from T-1629's
land, same shape T-1958 fixed hours earlier). Docs-only single-line fix,
no code changed; existing CLI-dispatch integration test recorded as
evidence per the docs-only-ticket precedent.

### Changed
```
 docs/modules/gates.md              |  2 +-
 tickets/T-draft-46574f02/ticket.md | 25 +++++++++++++++++++++++++
 2 files changed, 26 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 1130 warning(s), 709 waived
- error-findings: ARCH001@src/frob/tickets/_land.py
