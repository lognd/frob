---
id: T-0527
title: SCOPE001 cross-ticket exemption breaks on a plain merge commit with no ticket
  reference
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: T-0527 needs a merge-commit regression test fixture in the existing SCOPE001/T-0108
    exemption test class
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'sequential single-worktree dispatch: T-0526''s committed files (dsl.py)
    still show in the diff-vs-main SCOPE001 check for T-0527 (T-0108/T-0412 precedent)
    since one of T-0526''s commit subjects did not carry a T-0526 reference'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'sequential single-worktree dispatch: T-0526''s committed files (test_dsl.py)
    still show in the diff-vs-main SCOPE001 check for T-0527 (T-0108/T-0412 precedent)'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestScopePrework::test_scope001_merge_commit_with_no_ticket_ref_falls_back_to_parent
designated_repro_test: null
threat: null
component: null
---
Found while working T-0513 in a sequential-tickets-in-one-worktree flow: SCOPE001's T-0108 cross-ticket exemption (a file already committed entirely under another ticket's own scope is exempt) stopped recognizing CHANGELOG.md/pyproject.toml/uv.lock as exempt for T-0513's own frob check --ticket run, even though the LATEST commit touching them (chore(release): re-stamp 0.57.0 after main merge, T-0512 done report) references T-0512 and T-0512's scope was extended to cover exactly those files. Root cause suspected: a plain 'git merge main' merge commit in the history also touches these files (conflict resolution) and carries NO ticket reference at all in its message, defeating whatever per-commit ticket-reference check the exemption performs. Needs investigation into _scope_gate_check_file / the T-0108 exemption's commit-walking logic to see if a merge commit should be transparently skipped (its content is just main's own already-scoped history, not new unscoped work) rather than treated as an unattributed touch.