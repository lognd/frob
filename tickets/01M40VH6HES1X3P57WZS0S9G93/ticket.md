+++
id = "01M40VH6HES1X3P57WZS0S9G93"
title = "gob-exec: clear the child environment and pass an explicit allowlist"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T12:23:57Z"
updated = "2026-10-08T12:48:55Z"
idempotency_key = "m2-gobexec-env-clear"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-exec/**"]

[[acceptance]]
text = "Given a spawn with env_clear and an allowlist, when the child prints its environment, then only allowlisted and added variables are present"
bound = true
+++

Found on ~4PT3KZB: gob-exec Spec.env only adds variables to the inherited environment; it cannot clear it. security.md 2.4 (tool stages run with a scrubbed environment) and 2.5 (the sandbox worker starts with an empty environment; the broker answers only granted names) need an env_clear option plus an explicit allowlist of inherited names (for example PATH, HOME, and per-spawn additions such as GH_TOKEN for gh). Add it, use it where a spawn needs only specific variables, and test that a variable not on the allowlist does not reach the child.
