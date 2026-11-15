+++
id = "01M7EXVK6WCDD7HFKRD4XPDRQ0"
title = "grimble-model: MDL000 for reserved word 'tests' suggests a name"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:03Z"
updated = "2026-11-15T06:21:03Z"
labels = ["no-story"]

[[acceptance]]
text = "A node named tests parses or the error carries a suggestion"
bound = false

[[acceptance]]
text = "SPEC 2.6 matches"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md L4. node tests gives MDL000 reserved word (SPEC 2.6 line 244). Remedy: suggest an alternate name or un-reserve in entity-name position.
