---
id: T-0323
title: 'git merge driver for tickets.md: auto splice_ledger via .gitattributes'
state: done
kind: bug
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- .gitattributes
- src/frob/tickets/**
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/**
- tests/test_ticket_merge_driver.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_same_id_newer_state_wins_and_is_written_back
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched
designated_repro_test: null
threat: null
component: null
---
Every worktree merge both-sides-appends tickets.md and conflicts; the coordinator ran splice_ledger by hand ~8 times this session, and the evidence: yaml field kept getting clobbered (re-recorded evidence on ~5 tickets). Register a git merge driver (frob tickets merge-driver) wired via .gitattributes so  auto-resolves both-sides-append conflicts with splice_ledger (dedupe by id, archive-aware, preserve evidence). Eliminates manual splicing AND the evidence-lost-in-merge class. Consider also storing evidence in a merge-robust form so it survives.