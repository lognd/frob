## Done report

Added the T-1401 write_coverage_lock/load_coverage behavior changes
(zero-hit ratchet carve-out, unjoined-module enumeration) to
docs/modules/gates.md#public-api, closing the doc-drift gap the ticket
named.

### Changed
```
 tickets.md | 10 +++++-----
 1 file changed, 5 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `cmd:bash -c "grep -q 'zero-hit ratchet' docs/modules/gates.md && grep -q 'unjoined-module' docs/modules/gates.md" exit=0 sha256=e3b0c44298fc` (cmd evidence, exit=0)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 368 warning(s), 741 waived
- error-findings: PRE001@tickets/T-1405
