+++
id = "01M6PAP4QMGET4G1B4KVQKQPD1"
title = "Add a dedicated advisory Reason variant for warn-level CAP001 findings"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-11-05T17:04:15Z"
updated = "2026-11-05T17:04:15Z"
scope = ["crates/gob-rules/src/types.rs"]
+++

Follow-up of ~K4EMP90. Warn-level atoms are emitted Unresolved with Reason::MayOnlyOwner, a poor fit; gob_rules::Severity has no Warn.
