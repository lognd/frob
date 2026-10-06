+++
id = "01M48PBZ7A1DSJJW9ZDKCJ0F5T"
title = "gob-mdtest: column and message assertions, own-line and stacked markers, bare marker with a default rule"
type = "story"
category = "todo"
priority = "high"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:38Z"
updated = "2026-10-06T13:41:04Z"
scope = ["crates/gob-mdtest/**"]

[[acceptance]]
text = "parser unit tests cover each marker form"
bound = false

[[acceptance]]
text = "a failing self-test corpus exists for each mismatch kind (rule, column, message)"
bound = false

[[acceptance]]
text = "FORMAT.md documents every form"
bound = false

[[acceptance]]
text = "marker words advisory and unresolved[REASON] (with required) exist and take column and message"
bound = false

[[acceptance]]
text = "a self-test fails on expected unresolved but got error, and on a differing reason"
bound = false
+++

Extend markers to `error: [COL] RULE "substring"` (1-based column, message contains), allow a marker on its own line applying to the next non-marker line and stacked markers, and add a default rule so a bare `error:` in a rule-docs corpus means that rule (ty assertion syntax). Prerequisite for executable rule docs (~D3ZK8NM). Source: notes/research/rule-testing.md (D103).
