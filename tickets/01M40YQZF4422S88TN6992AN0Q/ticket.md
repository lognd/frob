+++
id = "01M40YQZF4422S88TN6992AN0Q"
title = "Remedies name commands that do not exist (frob lease release); test every remedy against the CLI registry"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T13:20:05Z"
updated = "2026-10-03T14:02:44Z"
idempotency_key = "m2-rel-remedy-commands-exist"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob/src/cycle_cmd.rs", "crates/frob/tests/remedies.rs", "crates/gob-cli/src/cli.rs", "crates/frob/Cargo.toml", "Cargo.lock", "crates/gob-directives/src/scan.rs", "crates/gob-directives/src/rules.rs", "crates/gob-directives/tests/scan.rs", "docs/reference/rules/DSL002.md", "changelog.d/01M40YQZF4422S88TN6992AN0Q.fixed.md"]

[[acceptance]]
text = "Given every remedy string frob can emit, when the remedy test runs, then each frob command and flag it names exists in the CLI registry"
bound = true
+++

Found while closing this repository's cycle: E-CYCLE-LEASE's remedy says to run frob lease release and ticket update --category todo, but there is no lease release verb and the verb that releases a lease and returns a ticket to todo is frob requeue <ticket> --reason <why>. A remedy that names a command that does not exist teaches the wrong thing. Fix the remedy to name frob requeue (or finishing and landing the ticket), and add a test that every remedy string emitted by frob names only commands and flags that exist: parse remedies in the error catalogue (and the strings in cycle_cmd.rs, milestone_cmd.rs, release_cmd.rs, first_run.rs, land and lease) for `frob <verb path> --flag` spans and check them against the CLI registry, the same check SYNC009 (unknown-cli-reference) will do for docs.
