+++
id = "01M4DYPFE1Z7MXVNG8MJ7N30N5"
title = "gob-exec: redact secrets only in transcripts and stderr, never in the parsed payload a tool returns"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T14:29:23Z"
updated = "2026-10-08T14:29:23Z"
scope = ["changelog.d/**", "crates/gob-exec/**"]

[[acceptance]]
text = "Given a tool whose stdout payload contains a secret-looking string, when parsed, then the payload is intact and the transcript is redacted"
bound = false
+++

Follow-up from ~ZZCCYHY: runner-captured output passes the secret redactor, which can mangle legitimate content (CSS with secret= patterns).
