+++
id = "01M4XJ9HA1C3KVG78XF5YAFTXP"
title = "GRL lowering: 'is snippet as roles' lifts to universal role nodes"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T16:00:27Z"
updated = "2026-10-14T16:00:27Z"
scope = ["crates/gob-plan/**"]

[[acceptance]]
text = "'is snippet as roles' lowers and matches in every language"
bound = false

[[acceptance]]
text = "metavariables bind as role nodes usable by the rest of the rule"
bound = false
+++

Follow-up of ~H2V8QVT. Needs a role-lifting step (snippet parsed in its tagged language, lifted to universal operators, GRL007 for unliftable nodes) and a role-binding plan op binding metavariables from gob_pattern::grammar Match.bindings as role nodes; no lifting exists in gob-pattern today.
