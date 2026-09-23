---
id: T-5108
title: narrative move deletes directive lines inside the moved comment run
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4694
parent: T-4691
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/narrative/_cli.py
- tests/test_narrative_migrate.py
- docs/commands/narrative.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_narrative_migrate.py
  reason: positive control and regression test for the directive-preservation fix
    must live in the existing CLI test file
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/narrative.md
  reason: document the new default directive-preservation behavior this fix adds to
    frob narrative move
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/test_narrative_migrate.py::TestDirectiveLinesPreserved::test_directive_keep_lines_finds_lead_and_continuation_lines
- tests/test_narrative_migrate.py::TestDirectiveLinesPreserved::test_positive_control_keeps_directives_moves_only_prose
- tests/test_narrative_migrate.py::TestDirectiveLinesPreserved::test_diff_of_moved_file_removes_no_directive_line
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5108
branch: t-5108
---
Measured 2026-09-19 by the narrative cluster agent working T-4719, T-4723 and T-4715: the narrative move verb's default mode (without keep-file) deletes the entire contiguous comment run it is pointed at, including directive lines that sit inside that run next to the prose. Lost in three separate runs and restored by hand before commit: frob:doc anchors, a frob:waive PII012, and a frob:invariant INV-042 block.

Why this is structural: the DOCARCH cleanup moves hundreds of runs, and the planned Tier-A auto-fix (T-4694) will call the same path unattended, so every directive adjacent to prose would silently vanish and the graph would lose edges, waivers and invariants with no gate firing.

Fix: when moving a run, split it at token level into prose lines and directive lines (any line whose first token after the comment marker is a frob: directive, plus the continuation lines of a multi-line directive block) and keep the directive lines in place; only the prose leaves. Positive control: a fixture run containing prose plus one frob:doc, one frob:waive and one multi-line frob:invariant must, after move, still contain all three directives byte-for-byte and none of the prose. Also cover the agent's detection recipe as a regression test: the diff of a moved file must contain no removed directive lines.