+++
id = "01M5KE9866QXR3E94E7J94DZY4"
title = "frob-cli: drift test for grimble-ci static frob verb table"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T03:53:41Z"
updated = "2026-10-23T04:25:36Z"
scope = ["crates/frob-cli/**", "crates/grimble-ci/**", "crates/frob/**"]

[[acceptance]]
text = "a frob-cli test fails when the grimble-ci static verb table differs from the real clap verb tree"
bound = true

[[acceptance]]
text = "the test passes when the table matches the tree"
bound = false
+++

grimble-ci CI012 (T040N) judges workflow frob verbs against a static VERBS table in crates/grimble-ci/src/verbs.rs because layering forbids depending on the CLI tree. Add a test in frob-cli that walks the real clap verb tree and fails when the table differs.
