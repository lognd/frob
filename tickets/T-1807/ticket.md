---
id: T-1807
title: WIRE001 dict-table pattern misses module-qualified dict values (_tools.X in
  _TOOL_DISPATCH)
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
