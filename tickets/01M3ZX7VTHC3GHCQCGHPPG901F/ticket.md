+++
id = "01M3ZX7VTHC3GHCQCGHPPG901F"
title = "This repository's own tool stages need one-time trust (maintainer step and CI flag)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-09T20:43:05Z"
idempotency_key = "m2-sec-self-trust"
labels = ["milestone:2", "area:security"]
scope = ["frob.toml", ".github/workflows/ci.yml", "docs/design/security.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7V9AKM8KVBHF32BWEC3K"

[[links]]
kind = "blocked-by"
target = "01M3ZX7VPGRERTZNVS5VR437JY"

[[acceptance]]
text = "Given a fresh clone and an untrusted cargo dev gen stage, when check runs, then the stage is Unresolved untrusted with the trust command in the remedy"
bound = false

[[acceptance]]
text = "Given the CI workflow, when it runs check, then it uses --trust-from and no other trust flag"
bound = false
+++

Implements security.md sections 2.4 and 5 item 3 (OWNER call).

After process packs land: document `frob trust --follow origin/experimental` once per machine, switch CI to --trust-from. Open owner call: agents cannot run it, so each agent machine needs a person to do it once; confirm the policy before this lands.
