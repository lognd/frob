+++
id = "01M69AHE7ZK46M5EV1J2XRXGMP"
title = "decisions.toml: a real citations field and one-line-anchor homes"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 2
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:51:33Z"
updated = "2026-11-01T14:45:23Z"
idempotency_key = "grmb-cycle1-decision-citations"
scope = ["crates/gob-dev/src/render/decisions.rs", "docs/decisions/**", "changelog.d/01M69AHE7ZK46M5EV1J2XRXGMP.changed.md", "docs/decisions/README.md", "docs/decisions/decisions.toml"]

[[acceptance]]
text = "decisions.toml accepts an optional citations list per decision, the generated log renders it, and the D150-D165 comment lines become that field"
bound = true

[[acceptance]]
text = "The generator doc comment and the decisions.toml header agree that the decision text lives in the toml and the home heading is an anchor"
bound = true
+++

Follow-up of ~MHGA5VN cycle 1: deny_unknown_fields refuses a citations key, so cycle 1 wrote citations as TOML comments.
