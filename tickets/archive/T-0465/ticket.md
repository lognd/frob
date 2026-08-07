---
id: T-0465
title: 'hazard: agents editing .git/info/exclude pollute ALL worktrees + main (shared
  common dir) -- an agent excluded src/frob/render/ to hide untracked files and silently
  un-tracked the whole T-0448 foundation; guard/lint against it + playbook rule'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
- src/frob/gates/
- tests/test_gates.py
- docs/modules/gates.md
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0465 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md rule-catalog entry for EXCL001; REL001 bump for new
    public API exclude_hazard_gate
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: docs/modules/gates.md rule-catalog entry for EXCL001; REL001 bump for new
    public API exclude_hazard_gate
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: docs/modules/gates.md rule-catalog entry for EXCL001; REL001 bump for new
    public API exclude_hazard_gate
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: docs/modules/gates.md rule-catalog entry for EXCL001; REL001 bump for new
    public API exclude_hazard_gate
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: docs/modules/gates.md rule-catalog entry for EXCL001; REL001 bump for new
    public API exclude_hazard_gate
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestExcludeHazardGate::test_entry_shadowing_tracked_dir_fires
- tests/test_gates.py::TestExcludeHazardGate::test_entry_matching_no_tracked_path_is_silent
- tests/test_gates.py::TestExcludeHazardGate::test_comment_and_negated_lines_are_ignored
- tests/test_gates.py::TestExcludeHazardGate::test_exact_tracked_file_entry_fires
- tests/test_gates.py::TestExcludeHazardGate::test_empty_exclude_file_is_silent
- tests/test_gates.py::TestExcludeHazardGate::test_non_git_root_is_silent
designated_repro_test: null
threat: null
component: null
---
