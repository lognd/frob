+++
id = "01M3ZX7VYSYT45N8ZKZJQ2DY5D"
title = "Effect classes: ordinary, secret-shaped, control plane, privilege"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-03T03:34:34Z"
idempotency_key = "m2-sec-effect-classes"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/effects/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given a grant fs.read of `**`, when evaluating a read of .env, then it is denied because secret-shaped is a separate effect"
bound = false

[[acceptance]]
text = "Given a grant of fs.write.control over .git/**, when parsed, then it is refused as not grantable"
bound = false
+++

Implements security.md section 2.6 (I6, I8, I10).

Exact, least-privilege, expiring grants; secret-shaped scopes are a separate named effect never implied by a glob and never granted by base-ref trust when new, every byte read registered with the gob-log redactor; control-plane writes never satisfied by a glob or CI trust; .git, the trust store and caches are not grantable; privilege class covers replaces, fix.machine, subprocess.
