+++
id = "01M7EXVMKCA66CSDE6H315STRP"
title = "grimble docs: implementation-status table per SPEC section; fix 4.10 EBNF for vmodel verified_by"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:04Z"
updated = "2026-11-15T06:21:04Z"
labels = ["no-story"]

[[acceptance]]
text = "Each SPEC section carries an implemented/partial/not row"
bound = false

[[acceptance]]
text = "4.10 EBNF matches 4.5"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md L12. All docs Status: draft while SPEC claims normative; SPEC 4.10 EBNF line 879 lists only runnable/manual for vmodel while 4.5 shows verified_by. Note overlaps ticket for H4 (F9ZNSC3).
