+++
id = "01M4CTTZGDBKBNQ0CTEYYJGRFJ"
title = "Definition of done per ticket type: epics and docs tickets are not asked for a changelog fragment or measured evidence by default"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:42Z"
updated = "2026-10-22T01:38:17Z"
scope = ["changelog.d/**", "crates/frob-pm/**", "crates/frob-ledger/**", "crates/frob-release/**", "crates/frob-evidence/Cargo.toml", "crates/frob-evidence/src", "crates/frob-evidence/tests", "crates/frob-check/Cargo.toml", "crates/frob-check/benches", "crates/frob-check/clippy.toml", "crates/frob-check/src", "crates/frob-check/tests", "docs/design/tickets.md", "docs/design/pm-enforcement.md", "docs/reference/config.md", "docs/schemas/config.json", "docs/reference/rules/REL003.md", "docs/guides/quickstart.md", "crates/frob-evidence/src/done.rs", "crates/frob-evidence/tests/**", "crates/frob-check/src/product.rs", "docs/design/documentation.md"]

[[acceptance]]
text = "Given an epic whose children are done, when it closes, then no changelog fragment or command evidence is required by default"
bound = true

[[acceptance]]
text = "Given a docs ticket, when it closes, then no changelog fragment is required by default but an invalid fragment it carries is still refused"
bound = true

[[acceptance]]
text = "Given a task, bug or custom ticket with no fragment, when it closes, then the changelog fragment is still required"
bound = true

[[acceptance]]
text = "Given [pm] changelog_exempt_types is empty or lists other types, when a ticket closes, then the exemption follows the setting"
bound = false

[[acceptance]]
text = "Given an exempt ticket type, when check --ticket runs REL003, then a missing fragment is not reported"
bound = false

[[acceptance]]
text = "Given the config, when changelog_exempt_types is unset or names an unknown type, then it defaults to epic and docs or is rejected at load"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM.
