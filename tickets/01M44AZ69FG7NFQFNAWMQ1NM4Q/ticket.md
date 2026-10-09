+++
id = "01M44AZ69FG7NFQFNAWMQ1NM4Q"
title = "frob serve: read-only MCP surface generated from verb metadata"
type = "story"
category = "in-progress"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-04T20:51:28Z"
updated = "2026-10-09T17:24:58Z"
scope = ["crates/gob-cli/**", "crates/gob-macros/src/command.rs", "crates/gob-product/src/**", "crates/frob/src/board_cmd.rs", "crates/frob/src/config_cmd.rs", "crates/frob/src/cycle_cmd.rs", "crates/frob/src/milestone_cmd.rs", "crates/frob/src/milestone_evidence_cmd.rs", "crates/frob/src/release_cmd.rs", "crates/frob-ack/src/cmd.rs", "crates/frob-check/src/verb.rs", "docs/design/cli.md", "docs/design/README.md"]

[[acceptance]]
text = "Given the verb registry, when frob serve starts, then every read-only verb is listed as an MCP tool whose input schema equals the verb schema"
bound = false

[[acceptance]]
text = "Given an MCP tool call, when it runs, then the result is the same JSON envelope the CLI prints for that verb"
bound = false

[[acceptance]]
text = "Given a mutating verb, when serve lists tools, then it is absent"
bound = false
+++

Coordinator decision 2026-10-04 (owner delegated; review notes/review/v1-gap/C-features.md P-04): frob serve is kept, as a thin MCP surface generated from command metadata, not a hand-written server. Every verb already has a typed schema and a JSON envelope; serve exposes read-only verbs (ticket show/list/doable/brief, check --json, lease list, doctor, explain) as MCP tools whose input schema and output are the verb schema and envelope, so there is no second API to keep in sync. Mutating verbs stay CLI-only until a later decision. Sequenced after 0.532.0 and the Python adapter epic; low priority. Record a decision row in docs/design/README.md and a section in docs/design/cli.md.
