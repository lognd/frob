+++
id = "01M4XHE31F38EKXKGHCPQV03PB"
title = "CLI flags declared once: convert remaining string-name flag lookups in gob-product and gob-testsupport"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T15:45:28Z"
updated = "2026-10-27T02:58:19Z"
scope = ["crates/gob-product/**", "crates/gob-testsupport/**", "crates/gob-cli/**"]

[[acceptance]]
text = "Given gob-product and gob-testsupport, when flags_declared_once runs, then no string-name flag lookup remains"
bound = false
+++

Follow-up of ~6T3ZQX6. String-name flag lookups remain in gob-product (shared_flags, check.rs, doctor.rs) and gob-testsupport fake bins. Convert to clap::Args structs via gob_cli::augment/parse and extend crates/gob-cli/tests/flags_declared_once.rs to cover them. Also dedupe rule_cmd.rs between crates/frob and crates/grimble.
