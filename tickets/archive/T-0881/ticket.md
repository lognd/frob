---
id: T-0881
title: 'COV001/DOC002: exports_consumers frob:doc anchor mismatch (T-0858 landing)'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/exports/__init__.py
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while verifying gates for T-0708/T-0860/T-0725 (unrelated strata/native-missing
work) in a worktree merged to main tip 4b43609f: `frob check --only coverage` reports
COV001 (missing frob:doc edge) for src/frob/exports/__init__.py::ConsumerRef,
ConsumersResult, ConsumersResult.as_text, ConsumersResult.as_json, exports_consumers,
plus a DOC002 (broken anchor) for the same symbols' `frob:doc
docs/modules/cli.md#exports-consumers-t-0858` directive: the computed slug
`#exports-consumers-t-0858` does not resolve against docs/modules/cli.md, which
actually has the anchor spelled `exports-consumers-surface-t-0858` (an extra
"-surface"). This is pre-existing on main as landed by T-0858
(0c1ed8cf07e07a9c3660da30a873e1429a55d545, "land T-0858 xref sunset reevaluation") --
none of src/frob/exports/**, docs/modules/cli.md were touched by T-0708/T-0860/T-0725.
Fix: either rename the anchor in docs/modules/cli.md to match the directive, or fix the
five `frob:doc` directives in src/frob/exports/__init__.py to point at the anchor's
real spelling.

## Drop reason
- 2026-07-23: superseded: fixed upstream by whatever landed on main during this session -- src/frob/exports/__init__.py's frob:doc anchors already read exports-consumers-surface-t-0858 (the correct spelling) after merging main; COV001/DOC002 confirmed 0 errors for this file post-merge