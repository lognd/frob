+++
id = "01M3ZX7Z0EM0DCAHC59PJH50MJ"
title = "Escape control, bidi and invisible characters in rendered text"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:37Z"
updated = "2026-10-04T13:51:26Z"
idempotency_key = "m2-sec-escape-controls"
labels = ["milestone:2", "area:security", "good-first"]
scope = ["crates/gob-diagnostics/src/escape.rs", "crates/gob-diagnostics/src/text.rs", "crates/frob-evidence/src/attestation.rs", "crates/gob-diagnostics/src/lib.rs", "crates/gob-diagnostics/Cargo.toml", "Cargo.lock", "crates/gob-diagnostics/tests/contract.rs", "changelog.d/01M3ZX7Z0EM0DCAHC59PJH50MJ.changed.md"]

[[acceptance]]
text = "Given a message containing ESC [ 31 m and a right-to-left override, when rendered as text, then both appear as escapes and no control byte reaches the terminal"
bound = true

[[acceptance]]
text = "Given the same message, when rendered as JSON, then the original string is preserved exactly"
bound = true
+++

Implements security.md section 2.10 (escaping); diagnostics.md section 2.

Pure function plus renderer hook: every C0 and C1 control except newline and every bidi and invisible formatting character is escaped everywhere in text mode; JSON keeps exact strings.
