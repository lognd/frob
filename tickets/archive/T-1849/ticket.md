---
id: T-1849
title: frob:waive comments under .claude/hooks/ never bind (graph prunes .claude entirely)
state: dropped
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/excludes.py
- src/frob/gates/_pii_structural/_self_match.py
- src/frob/gates/_pii_structural/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob:waive comments placed inside .claude/hooks/*.py can never take
effect: frob.graph.build_graph's file walk prunes the entire .claude/
directory (src/frob/excludes.py's BUILTIN_SKIP_DIRS includes ".claude"),
so no WAIVE edge is ever created for anything under it -- confirmed via
sqlite3 query against .frob/cache.db (zero rows in `files` for any
.claude/** path). Meanwhile pii_structural_gate (SEC110/PII010/PII012)
scans hooks via a plain `git ls-files`-style walk that is NOT graph-walk
pruned, so it fires on .claude/hooks/*.py regardless.

Net effect: any SEC110/PII finding under .claude/hooks/ is structurally
unwaivable via the normal frob:waive comment mechanism, even though at
least one existing comment in this tree (.claude/hooks/diagnosis-nudge.py
PII012) is written as if it works. Discovered while working T-1839
(SEC110 in .claude/hooks/dispatch-telemetry.py); T-1839 was failed
rather than worked around.

Fix direction (either is plausible, pick one during triage):
- carve .claude/hooks/** out of BUILTIN_SKIP_DIRS's prune (or add a
  narrower graph-walk exception) so directive comments there are ingested
  like any other tracked source, OR
- add .claude/hooks/*.py to _SELF_EXCLUDED_FILES in
  src/frob/gates/_pii_structural/_self_match.py if hook scripts are
  meant to sit outside this gate's obligation surface entirely, OR
- teach pii_structural_gate to honor the same BUILTIN_SKIP_DIRS/[graph]
  exclude pruning the rest of the graph respects, so it never flags a
  file it structurally cannot let get waived.

## Drop reason
- 2026-08-08: duplicate of T-1838, same root cause (BUILTIN_SKIP_DIRS pruning .claude from frob.graph's walk) and same fix (removed .claude from BUILTIN_SKIP_DIRS, kept nested-worktree pruning via _is_nested_worktree); T-1838 lands the fix (absorbed by T-1838)
