+++
id = "01M66JFKP9Z3MDAQBJ1WG59YDC"
title = "Dedupe agent marker lists onto the gob-cli audience module"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-30T14:12:38Z"
updated = "2026-11-06T19:37:57Z"
scope = ["crates/grimble/**, crates/gob-trust/**, crates/gob-cli/**", "crates/gob-trust/**", "crates/gob-cli/**", "crates/grimble/**"]

[[acceptance]]
text = "grimble presence AGENT_MARKERS and gob-trust prompt list reuse one shared marker list"
bound = true
+++

found while working 01M63B7F02SKSJCQG7TMXQ4HW5: three divergent agent-marker lists now exist.
