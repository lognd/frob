+++
id = "01M4DVX007B7659YHBWVQK2ZMX"
title = "docs/crunk/README.md: document the tokens verb, the token exports and the Tailwind runtime"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-10-08T13:40:25Z"
updated = "2026-11-15T04:28:02Z"
labels = ["area:crunk"]
scope = ["docs/crunk/README.md", "docs/guides/crunk.md"]

[[acceptance]]
text = "docs/guides/crunk.md documents every tokens target, the file and drift table, E-SPEC exit 3 and the Tailwind runtime bridge, with a crunk <verb> row per verb"
bound = true
+++

Found while working ~M635E0X and ~1WS0DQ4: the docs/crunk lease was held by another ticket, so the verb table, the Token exports section, E-SPEC exit-3 note and the runtime bridge notes live in crates/crunk-tokens/README.md and crates/crunk-tailwind/README.md. Move or link them from docs/crunk/README.md.
