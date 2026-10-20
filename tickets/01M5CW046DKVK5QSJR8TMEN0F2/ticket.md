+++
id = "01M5CW046DKVK5QSJR8TMEN0F2"
title = "Refresh state and remote probe"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T16:37:49Z"
idempotency_key = "dt-DT05"

[[acceptance]]
text = "The remote probe never prompts: ls-remote runs with terminal prompts off and ssh BatchMode"
bound = true

[[acceptance]]
text = "Probe results are cached in refresh.toml and failures back off exponentially"
bound = true

[[acceptance]]
text = "A held refresh lock yields the cached state instead of a second probe"
bound = true

[[acceptance]]
text = "frob refresh --status reads only the cache and takes under 10 ms"
bound = true

[[acceptance]]
text = "A missing base on the remote exits 1 with E-SYNC-NO-BASE naming the remote HEAD"
bound = true

[[acceptance]]
text = "An unreachable remote exits 3 with a W-SYNC warning class"
bound = false
+++

refresh.toml state, bounded non-prompting ls-remote (2.5s), backoff, lock, frob refresh --status under 10ms, remote and base validation. See docs/design/distributed-tickets.md.
