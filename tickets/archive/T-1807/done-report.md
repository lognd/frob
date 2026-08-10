## Done report

Widened WIRE001's dict-table wiring-reach pattern (src/frob/gates/_wire.py
::_wire_reach_patterns) so the `:\s*{short}\s*[,}]` alternative also
accepts an optional `name.`-qualified prefix ahead of the short symbol
name, matching the module-qualified dict-value shape every row of
src/frob/serve/_socketd.py::_TOOL_DISPATCH uses
(`"frob_map": _tools.frob_map,`). Before this fix the regex required
`short` to sit immediately after the colon, so every existing
_TOOL_DISPATCH entry would have been a WIRE001 false positive if it were
freshly added -- only pre-existing-symbol diff-scoping was grandfathering
them in.

Added a regression test proving a module-qualified dict-table value
counts as reached the same way a bare one already did.

Also retired the now-obsolete WIRE001 waiver on
src/frob/serve/_tools.py::frob_map -- its own comment named T-1807 as
follow_up and existed solely because of this exact regex gap; land's
LiveTrackerCited gate required re-pointing or removing it in this same
change. Verified WIRE001 stays clean (0 errors) against the real repo
with the waiver removed.

### Changed
```
 src/frob/gates/_wire.py       |  7 ++++++-
 tests/test_gates.py           | 33 +++++++++++++++++++++++++++++++++
 tickets/T-1807/done-report.md | 29 +++++++++++++++++++++++++++++
 tickets/T-1807/ticket.md      | 15 +++++++++++++--
 4 files changed, 81 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_function_reached_via_module_qualified_dict_table_value_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 680 warning(s), 733 waived
- error-findings: PRE001@tickets/T-1807, invalid-assignment@tests/test_ticket_land.py
