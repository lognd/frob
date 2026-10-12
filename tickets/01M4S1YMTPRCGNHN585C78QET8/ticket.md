+++
id = "01M4S1YMTPRCGNHN585C78QET8"
title = "gob-diagnostics: add message origin to EnvelopeError and re-export TextOrigin"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-12T21:57:56Z"
updated = "2026-10-12T23:54:51Z"
scope = ["crates/gob-cli/src/render.rs"]
+++

~Q85F72V added FindingRecord.message_origin (TextOrigin) but left EnvelopeError without an origin and did not re-export TextOrigin from lib.rs; the struct literals in gob-cli render.rs and refusal.rs are affected. Acceptance: EnvelopeError carries an origin serialized like findings, TextOrigin is re-exported, schema envelope.json updated, nextest tests bound.
