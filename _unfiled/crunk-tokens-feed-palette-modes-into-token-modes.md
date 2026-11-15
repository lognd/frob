+++
id = "01M7EXS9F60CP83A9BK9W5FC9P"
title = "crunk tokens: feed [palette.modes] into Token::modes"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETK97Q5VJ027ZV8AFBJWRQ"
reporter = "lognd"
created = "2026-11-15T06:19:47Z"
updated = "2026-11-15T06:19:47Z"
idempotency_key = "crunkplan-97b2b7425fdf"
labels = ["no-story"]

[[acceptance]]
text = "a spec with dark mode yields tokens whose modes map is populated (unit test)"
bound = false

[[acceptance]]
text = "unknown mode names produce a typed error"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H5.
Evidence: palette modes are parsed but never reach Token::modes, so exports ignore them
Remedy: populate Token::modes from [palette.modes] in the spec loader
Crates/files: crates/crunk-spec, crates/crunk-tokens
Verify against HEAD first; the audit ran on a stale binary.
