---
id: T-1807
title: WIRE001 dict-table pattern misses module-qualified dict values (_tools.X in
  _TOOL_DISPATCH)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_wire.py
- src/frob/serve/_tools.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/_tools.py
  reason: the fix retires the WIRE001 waiver this file's own comment named T-1807
    as follow_up for; land's LiveTrackerCited gate requires re-pointing/removing it
    in this same change
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestWireGate::test_new_function_reached_via_module_qualified_dict_table_value_is_not_flagged
designated_repro_test: null
threat: null
component: null
---
Found while working T-1479. WIRE001's dict-table wiring recognition
(src/frob/gates/_wire.py::_wire_reach_patterns, T-1684's own precedent
comment: "a DICT-TABLE entry... is the third by-reference wiring shape")
only matches a BARE name immediately following the dict entry's colon:

    wrapper_pattern = re.compile(
        rf"(?<![A-Za-z0-9_.])(?:{marker_names})\s*\(\s*{short}\s*[,)]"
        rf"|:\s*{short}\s*[,}}]"
    )

The second alternative (`:\s*{short}\s*[,}}]`) requires `short` to appear
directly after the colon+whitespace -- a MODULE-QUALIFIED dict value
(`"frob_map": _tools.frob_map,`, the exact style every entry in
src/frob/serve/_socketd.py::_TOOL_DISPATCH uses) never matches, since
`_tools.` sits between the colon and the short name. Confirmed this is
not just T-1479's own new entry: EVERY existing _TOOL_DISPATCH row
(`frob_stats`, `frob_graph_query`, `frob_exports`, ...) has zero real
callers anywhere in the tree outside this same dict -- `grep -rn
"frob_stats("` finds only the def site. They are grandfathered only
because WIRE001 is diff-scoped (checks newly-added symbols, not
pre-existing ones) -- the exact same regex gap would fire on any of them
today if they were freshly added, same as it just did for frob_map.

Fix: widen the second alternative to also match a qualified-name suffix,
e.g. `(?:[A-Za-z_][A-Za-z0-9_]*\.)?{short}` in place of a bare `{short}`,
so `_tools.frob_map` (and any other `module.attr` dict-table value)
counts as reached the same way a bare name already does.

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
