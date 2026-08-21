---
id: T-2544
title: document tool_parse_failure_result in docs/modules/process.md and drop T-2537's
  AFFECT001 waivers
state: done
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/process.md
- src/frob/process/parsers/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:uv run pytest tests/unit/test_parser_failure_diagnostics.py -q exit=0 sha256=e6894dd97db4
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dad9d57333aa1b01a392b32fe2dfad30675ba84c
---
T-2537 added tool_parse_failure_result (src/frob/process/parsers/common.py)
and routed parse_ruff_json / parse_eslint / parse_junit_xml / valgrind's
XML branch through it, but could NOT update docs/modules/process.md: that
file was held by T-2374's live cross-worktree lease, and `frob ticket
scope --add` refused with ScopeLeaseConflict.

Consequence: four AFFECT001 findings are waived in-tree (one per touched
parser), and the public-api listing in docs/modules/process.md does not
mention the new helper.

Do, once T-2374 has landed:
- add `<!-- frob:describes src/frob/process/parsers/common.py::tool_parse_failure_result -->`
  next to the existing tool_crash_result describes-line;
- add the signature line to the ```python public-api block;
- add a short "Unparsable output is never silence (T-2537)" subsection
  stating that every parse-failure branch attaches a real error
  Diagnostic, that a clean run is unchanged (zero diagnostics, exit 0),
  and that T-2521's consumer-side guard stays as the second layer;
- remove the four `frob:waive AFFECT001` lines added by T-2537.

The exact prose was drafted and then reverted in T-2537's worktree; see
commit "chore(parsers): drop docs/modules/process.md edit" on branch
t-2537 for the text.