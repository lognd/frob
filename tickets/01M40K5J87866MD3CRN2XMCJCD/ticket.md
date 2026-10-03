+++
id = "01M40K5J87866MD3CRN2XMCJCD"
title = "cli.md: document E-NO-CONFIG and the verbs that run without frob.toml"
type = "docs"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T09:57:47Z"
updated = "2026-10-03T09:57:47Z"
idempotency_key = "m2-cli-no-config-doc"
labels = ["milestone:2", "good-first"]
scope = ["docs/design/cli.md"]

[[acceptance]]
text = "Given cli.md, when read, then E-NO-CONFIG and the config-free verbs are listed"
bound = false
+++

Follow-up of ~ANDZXZ4. ## Start here
Read crates/frob/src/first_run.rs (the guard, the exempt verb list, the message) and docs/design/cli.md (error codes and exit classes). Add E-NO-CONFIG (exit 3, remedy frob init or git init) and the list of verbs that work without frob.toml (doctor, init, schema, config show, config sync, merge-driver, plus --help and --schema) to cli.md. Test: frob check --ticket passes. Ask the coordinator if unsure.
