+++
id = "01M4S1YMTPRCGNHN585C78QET8"
title = "gob-diagnostics: add message origin to EnvelopeError and re-export TextOrigin"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-12T21:57:56Z"
updated = "2026-10-13T00:07:43Z"
scope = ["crates/gob-cli/src/render.rs", "crates/gob-diagnostics/src/envelope.rs", "crates/gob-diagnostics/src/lib.rs", "crates/gob-diagnostics/src/refusal.rs", "crates/gob-diagnostics/tests/contract.rs", "crates/gob-diagnostics/tests/snapshots/contract__json_refusal_snapshot.snap", "docs/schemas/envelope.json"]

[[acceptance]]
text = "EnvelopeError carries message_origin serialized like findings"
bound = true

[[acceptance]]
text = "TextOrigin is re-exported from gob-diagnostics lib.rs"
bound = true

[[acceptance]]
text = "docs/schemas/envelope.json regenerated and bound by nextest"
bound = true
+++

~Q85F72V added FindingRecord.message_origin (TextOrigin) but left EnvelopeError without an origin and did not re-export TextOrigin from lib.rs; the struct literals in gob-cli render.rs and refusal.rs are affected. Acceptance: EnvelopeError carries an origin serialized like findings, TextOrigin is re-exported, schema envelope.json updated, nextest tests bound.
