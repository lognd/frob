+++
id = "01M4XDJTERTTAZHGYFDKFEK2T8"
title = "gob-pattern: follows/precedes/regex combinators and metavariable constraints"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T14:38:09Z"
updated = "2026-10-28T12:55:55Z"
labels = ["no-story"]
scope = ["crates/gob-pattern/**"]

[[acceptance]]
text = "Given a rule with follows/precedes/regex and a metavariable constraint, when run over a fixture, then only constrained matches fire"
bound = false
+++

Split from ~NRQ4KHD. Add follows, precedes and regex combinators to the rule table and per-metavariable constraints (kind, regex) on grammar patterns.

no-story: internal engineering task in gob-pattern; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
