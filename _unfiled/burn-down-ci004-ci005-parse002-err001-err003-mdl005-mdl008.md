+++
id = "01M6FZNKG5R4P9A3M1RYK6QJA6"
title = "Burn down CI004 CI005 PARSE002 ERR001 ERR003 MDL005 MDL008 CAP001 and drop their off tables"
type = "chore"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-03T05:56:16Z"
updated = "2026-11-03T05:56:18Z"
scope = ["frob.toml", "design/model.grmb", ".github/workflows/**", "scripts/claude-hooks/frob-suggest.py", "packs/std/rules/TODO001.grl", "crates/crunk-ingest/src/facts.rs", "crates/frob-check/src/snapshot.rs", "crates/frob-land/src/lock.rs", "crates/frob-lease/src/store.rs", "crates/frob-ledger/src/branch.rs", "crates/frob-obligations/src/cov.rs", "crates/frob-worktree/src/post_commit.rs", "crates/frob/src/agent/engine.rs", "crates/gob-exec/src/runner.rs", "crates/gob-git/src/ledger.rs", "crates/gob-plan/tests/lower.rs", "crates/grimble-model/tests/corpus.rs"]

[[acceptance]]
text = "Zero findings for the eight rules; their off tables are deleted from frob.toml"
bound = false
+++

Owner directive: warnings to errors. Continues ~MTBE4QF for these rules.
