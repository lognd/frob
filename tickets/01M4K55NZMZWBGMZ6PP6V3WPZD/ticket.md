+++
id = "01M4K55NZMZWBGMZ6PP6V3WPZD"
title = "command evidence captures absolute home paths unscrubbed, so frob check fails TICK004 until frob ticket doctor --fix runs"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "Claude"
created = "2026-10-10T14:58:45Z"
updated = "2026-10-10T14:58:45Z"
scope = ["crates/frob-evidence/**"]

[[acceptance]]
text = "a command-provider evidence record never contains an absolute home path at capture time"
bound = false
+++

found while coordinating the drain: ~WXKT9TC cargo run -- doctor evidence tripped TICK004; scrubbed by ticket doctor --fix after the fact.
