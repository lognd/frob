---
id: T-draft-16d31169
title: 'frob-suggest: narrow rule verdicts per HOOK-AUDIT table (recursive-grep, deletes,
  version-skew, find, worktree, floor-count, ledger)'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: T-draft-8c7e665d
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
- .claude/hooks/_shellscan.py
- tests/test_hook_frob_suggest_rules.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: .claude/hooks/*
  reason: avoid lease collision with T-4689 on tool-call-telemetry.py; scope only
    to rule logic files
  actor: logan
  at: '2026-09-19'
- op: add
  glob: .claude/hooks/frob-suggest.py
  reason: avoid lease collision with T-4689 on tool-call-telemetry.py; scope only
    to rule logic files
  actor: logan
  at: '2026-09-19'
- op: add
  glob: .claude/hooks/_shellscan.py
  reason: avoid lease collision with T-4689 on tool-call-telemetry.py; scope only
    to rule logic files
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: avoid lease collision with T-4689 on tool-call-telemetry.py; scope only
    to rule logic files
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: tests/test_hook_frob_suggest.py
  reason: T-draft-36c347fe leases this test file and hasn't landed yet; will re-add
    once it lands
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_hook_frob_suggest_rules.py
  reason: golden tests for narrowed rule verdicts, in a new file to avoid lease collision
    with T-draft-36c347fe's tests/test_hook_frob_suggest.py
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: recursive-grep exemption handles trailing slash, glob, single-segment dir,
    trailing flags, quoted path, single file target, path outside repo; only bare
    repo-root walk blocks
  evidence: []
- text: hand-rename-edit-multifile and unscoped-symbol-search rules are deleted
  evidence: []
- text: frob-version-skew fires only for check/test/land/verify-class verbs, not --help/--version/show/which
    frob probes, and its message stops recommending uv tool upgrade frob, recommending
    uv run frob in the checkout instead
  evidence: []
- text: raw-find-name blocks only a find rooted at the repo root without a prune/maxdepth/not-path/exec/delete
  evidence: []
- text: raw-worktree narrows to targets under .claude/worktrees/
  evidence: []
- text: handrolled-floor-count exempts --help
  evidence: []
- text: hand-edit-ledger fires only for tickets/ under the repo root
  evidence: []
- text: every audited false positive in HOOK-AUDIT.md/hook-events.jsonl kind=block
    rows passes (no longer blocked), and every audited true positive still blocks,
    proven by golden tests
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 2 of T-draft-8c7e665d. See scratchpad/HOOK-AUDIT.md sections 1.1-1.9 and 3.1.