+++
id = "01M4D6NTFHJT2BRA8VCRD8WDJ4"
title = "land cache miss runs two checks; share one throwaway worktree"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:36Z"
updated = "2026-10-08T07:29:36Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given a cache miss, when land checks the base, then one worktree serves both passes"
bound = false
+++

Follow-up from ~KJ95784.
