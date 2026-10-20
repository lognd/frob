+++
id = "01M336K75DVQ77F1T5HAEZ64C5"
title = "test_release.py changelog-fragment-ownership check fails on dev tip"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:03Z"
aliases = ["T-5293"]
labels = ["milestone:0.534.0"]
scope = ["tests/test_release.py", "src/frob/release", "changelog.d/T-4759.md"]
+++

gh run 35717833933; re-verified on dev tip 3acf8c6b30: tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket fails standalone (not a fleet version-bump race -- reproduced serially, single test, clean checkout).

## Failure log
- 2026-09-23 attempt 1: TICK015: dead worktree (no live process holds worktree <worktree>/.claude/worktrees/t-5293), requeued by frob check

## Drop reason
- 2026-09-23: landed by content: changelog.d/T-4759.md is gone on dev via a sibling's --allow-cross-ticket land; its own land record was reset by TICK015 (T-5358) and re-landing an empty diff refuses
