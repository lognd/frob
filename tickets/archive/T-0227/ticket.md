---
id: T-0227
title: gitio treats untracked gitlink/directory as file (Errno 21 warning spam)
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gitio.py::TestWorkingDiff::test_untracked_directory_is_skipped_not_read_as_file
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 12: graphite has .claude/worktrees/lithos (gitlink); every frob check/test warns 'could not read untracked file ...: [Errno 21] Is a directory'. Skip directories/gitlinks from ls-files --others handling; regression test with an untracked dir.