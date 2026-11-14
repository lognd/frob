+++
id = "01M7BP3DVBGTPRC7R3THSP1Y5P"
title = "frob-release: wire epic_closed/ci_green providers and attester doctor check into the CLI so exit criteria bind"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-14T00:07:47Z"
updated = "2026-11-14T01:51:47Z"
idempotency_key = "skstfyn-wire"
scope = ["crates/frob/**"]
+++

Follow-up of ~SKSTFYN: criteria.rs has pure providers; the CLI must gather epic ticket states and committer emails, call bind_builtin/derive_epic_criteria and surface attester_problems in frob doctor.
