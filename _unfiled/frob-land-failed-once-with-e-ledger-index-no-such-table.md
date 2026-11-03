+++
id = "01M6F43S6MR0HN4ZW959V09WP7"
title = "frob land failed once with E-LEDGER-INDEX no such table: tickets in e2e_init_loop::loop_on_trunk without FROB_NO_SPECULATIVE_CHECK"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T21:54:40Z"
updated = "2026-11-03T05:56:40Z"
scope = ["crates/frob-ledger/**"]
+++

Found while working ~SW1KHNQ. With the workaround env removed, loop_on_trunk failed once (1 of ~10 runs, under load): land returned E-INTERNAL E-LEDGER-INDEX: no such table: tickets. Not reproduced on rerun. Suspect the post-commit background check and land touching the ledger index at once. The env workaround stays in e2e_init_loop.rs until this is understood.
