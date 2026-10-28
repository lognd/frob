+++
id = "01M4P2N1D8ZJN8A3EDD9T7ZT21"
title = "agent: frob agent hook handlers (pre-bash, pre-read, session-start, pre-compact, user-prompt, stop)"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:26Z"
updated = "2026-10-28T12:55:47Z"
labels = ["no-story"]
scope = ["crates/frob-cli/**"]

[[acceptance]]
text = "frob agent hook <event> reads Claude Code hook JSON on stdin and writes the decision JSON on stdout"
bound = false

[[acceptance]]
text = "pre-read denies whole-file reads of files over a configured size with an offset/limit hint"
bound = false

[[acceptance]]
text = "pre-bash redirects or bounds unbounded output and routes heavy commands through frob agent heavy"
bound = false

[[acceptance]]
text = "malformed stdin fails open with a warning, never blocks the agent"
bound = false
+++

no-story: internal engineering task in frob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
