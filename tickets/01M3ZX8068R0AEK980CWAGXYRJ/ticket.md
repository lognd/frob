+++
id = "01M3ZX8068R0AEK980CWAGXYRJ"
title = "replaces as a privilege: shadow run and divergence"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-replaces"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-packs/src/replaces.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FKFSHB8KZM2N4CNF0P9"

[[links]]
kind = "blocked-by"
target = "01M3ZX7V587K71E94E0AE4GWW8"

[[links]]
kind = "blocked-by"
target = "01M3ZX7X3RQTTR7V8JFRN8TQEK"

[[acceptance]]
text = "Given a pack replacing a std rule and a finding only the shadow produces, when check runs, then Unresolved replaced-divergence is reported"
bound = false

[[acceptance]]
text = "Given a pack replacing CAP004 without --allow-replace, when checked, then it is refused"
bound = false
+++

Implements security.md section 2.9; plugins.md section 6.1 (override row).

The replaced std rule keeps running as a shadow; a finding it produces that the replacement does not is Unresolved replaced-divergence (required for security-relevant families); replacing PACK, CAP004 or GATE needs --allow-replace ID on every invocation; a new replaces is a GATE001 weakening.
