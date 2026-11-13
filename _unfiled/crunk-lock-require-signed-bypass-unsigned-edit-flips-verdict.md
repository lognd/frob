+++
id = "01M7AV387JMHAXX80G1009RTBM"
title = "crunk.lock require_signed bypass: unsigned edit flips verdict"
type = "security"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-13T16:15:50Z"
labels = ["no-story"]
scope = ["crates/crunk-*/**"]

[[acceptance]]
text = "A test shows an unsigned flip fails require_signed."
bound = false
+++

H4: an unsigned commit can flip a signed rejected verdict to approved and still satisfy require_signed. Source: frob-audit-grimble-crunk.md (Opus audit).
