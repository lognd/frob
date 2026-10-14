+++
id = "01M4WGCDS34JR3PFCWKHZ73YP7"
title = "GRL lowering: snippets"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "Claude"
created = "2026-10-14T06:07:51Z"
updated = "2026-10-14T15:16:23Z"
scope = ["crates/gob-plan/**"]

[[links]]
kind = "blocked-by"
target = "01M4PPRHCTN3TZ0TJF8NRQ4KHD"

[[acceptance]]
text = "A snippet binder (find x: lang`pat`) and `x is` a snippet lower to a new MatchSnippet op, with the rule's single lang as the default language"
bound = true

[[acceptance]]
text = "The executor answers MatchSnippet exactly from grammar-level matches over the file text, and Unknown/Unresolved without text"
bound = true

[[acceptance]]
text = "MatchSnippet round-trips through the plan codec and validates; unsupported snippet forms (cast, as roles, no language) are refused by name"
bound = true
+++

Remaining slice of ~3A9N1B2 (slice 1, SCOPE001 glob sets, landed).
