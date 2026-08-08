---
id: T-1861
title: COV001/TEST001 fallout from T-1838 un-pruning .claude/hooks/** from the graph
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/**
- src/frob/gates/__init__.py
- design/frob.strata
- docs/guides/claude-hooks.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: added a real regression test for the TEST001 .claude/hooks/** exemption
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_claude_hooks_path
designated_repro_test: tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_claude_hooks_path
threat: null
component: null
---
T-1838 removed ".claude" from `frob.excludes.BUILTIN_SKIP_DIRS` so
`.claude/hooks/**` frob:waive comments resolve. Consequence not caught by
that ticket's own `--only lint`/`ty`-scoped verification: un-pruning a
directory from the graph walk exposes it to EVERY gate that reads the
graph, not just the WAIVE-edge resolver. A full unscoped `frob check
--json` on main now reports 13 errors, 11 new, all under `.claude/hooks/`
plus the new `design/frob.strata::claude_hooks` node T-1838 also added:

  COV001  .claude/hooks/_shellscan.py:39, :50
  COV001  .claude/hooks/diagnosis-nudge.py:245
  COV001  .claude/hooks/dispatch-telemetry.py:205
  COV001  .claude/hooks/frob-suggest.py:261
  COV001  .claude/hooks/frob-timeout-guard.py:19, :24, :30, :40
  COV001  .claude/hooks/sync-claude-config.py:130
  COV001  design/frob.strata:1395
  TEST001 .claude/hooks/_shellscan.py:50

Fix direction, coordinator-decided, both shapes applied per-rule rather
than uniformly:

- COV001 (doc edges): these ARE load-bearing -- every hook executes on
  every session, and dispatch-telemetry.py writes real telemetry. A
  `frob:doc` edge is cheap and these hooks genuinely need explaining.
  Give every flagged symbol (the 5 `main` entry points,
  `_shellscan.py`'s `POS`/`strip_quoted`, `frob-timeout-guard.py`'s
  `MIN_TIMEOUT_MS`/`PATTERN`/`REASON`, and the `claude_hooks` design node)
  a real `frob:doc` edge into a new doc home explaining what each hook
  does and why.

- TEST001 (exclude, not test): demanding pytest coverage of a Claude Code
  hook that only runs under the harness (stdin JSON payload, PreToolUse/
  Stop event dispatch) is the kind of obligation that gets waived
  repeatedly and becomes a tax, not real assurance -- `tests/
  test_hook_dispatch_telemetry.py`/`test_hook_diagnosis_nudge.py` already
  exist and exercise these hooks' real logic via direct import + stdin
  simulation for the ones that need it; TEST001 itself should exempt
  `.claude/hooks/**` by path the same way `_test001_002` already exempts
  `*.strata` files by extension (T-0168 precedent) -- a narrow,
  symmetric addition to the same predicate, not a directory-wide
  `frob:waive` (waived findings decay silently; an exempt PATH CLASS is
  visible and auditable the same way the `.strata` exemption already is).

Do not touch `design/frob.strata`'s own trust modeling further -- only
add the missing `frob:doc` edge for `claude_hooks`; the node's `may`
declarations are T-1838's, unchanged.