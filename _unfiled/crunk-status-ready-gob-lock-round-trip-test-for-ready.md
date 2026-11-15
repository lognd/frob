+++
id = "01M7FRSNZA2WKDWY7QBFRA675W"
title = "crunk status ready: gob-lock round-trip test for ready entries and red-lint refusal test"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-11-15T14:11:51Z"
updated = "2026-11-15T14:11:51Z"
idempotency_key = "gap-0md95w3"

[[acceptance]]
text = "Given a LockFile with ready entries, when written and read back, then they are equal"
bound = false

[[acceptance]]
text = "Given red lint findings, when status ready runs, then it refuses and names the findings"
bound = false
+++

Gaps from 0MD95W3: no round-trip test for LockFile::ready; refusal path untested; screens have no code-mapping field (approximated by non-empty sources).
