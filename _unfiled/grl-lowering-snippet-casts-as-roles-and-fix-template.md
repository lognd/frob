+++
id = "01M4XF8KYPGPRH6J6CAH2V8QVT"
title = "GRL lowering: snippet casts, as roles, and fix-template metavariables"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T15:07:32Z"
updated = "2026-10-14T16:01:15Z"
scope = ["crates/gob-plan/**"]

[[links]]
kind = "blocked-by"
target = "01M4WGCDS34JR3PFCWKHZ73YP7"

[[acceptance]]
text = "A snippet 'as KIND' cast lowers and filters the matched node by kind"
bound = true
+++

Follow-up of ~HZ73YP7. Lowering still refuses a snippet cast (as KIND), 'is ... as roles', and drops fix templates/metavariable bindings. Needs a role-binding op in the plan IR and executor wiring using gob_pattern::grammar Match.bindings.
