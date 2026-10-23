+++
id = "01M5KE9866QXR3E94E7J94DZY4"
title = "frob-cli: drift test for grimble-ci static frob verb table"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T03:53:41Z"
updated = "2026-10-23T03:53:41Z"
scope = ["crates/frob-cli/**"]
+++

grimble-ci CI012 (T040N) judges workflow frob verbs against a static VERBS table in crates/grimble-ci/src/verbs.rs because layering forbids depending on the CLI tree. Add a test in frob-cli that walks the real clap verb tree and fails when the table differs.
