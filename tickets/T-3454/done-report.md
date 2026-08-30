## Done report

Root cause: my T-3438 land added two `frob:tests` comments on
tests/unit/test_main_entry.py using pytest's own collect-only separator
(`Class::method`), but this repo's frob:tests graph convention is a
SINGLE `::` then a DOTTED `Class.method` qualname (matching every other
frob:tests directive in this file). The mismatched shape produced
DOC007 (target-form does not resolve) and DRIFT002 (the tests edge no
longer resolves) on both lines.

Fix: removed the two malformed self-referential frob:tests directives.
They were redundant anyway -- no other file in the codebase pointed at
these two new tests, and no sibling test in this file self-annotates
with a frob:tests comment naming itself.

Evidence:
- tests/unit/test_main_entry.py: 38/38 pass under -p no:xdist
- `frob check --only docblocks --only drift`: DOC007/DRIFT002 on
  tests/unit/test_main_entry.py:609 and :624 (both lines) are gone;
  gate:DOC dropped from 3 errors to 1 (the remaining 1 is T-3427's
  unrelated tickets/T-3411/ticket.md DOC006), gate:DRIFT dropped from 4
  errors to 2 (the remaining 2 are T-3428's/T-3441's unrelated
  DRIFT001 findings on _rapid_sweep.py/_scope.py)

### Changed
```
 tickets/T-3454/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_hook_suppresses_startup_warnings` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_without_hook_still_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 12 error(s), 4000 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3454, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
