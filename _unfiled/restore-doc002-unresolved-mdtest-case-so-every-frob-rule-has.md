+++
id = "01M5KRYDC70Q3YAYW6KXF9H0J6"
title = "Restore DOC002 unresolved mdtest case so every_frob_rule_has_a_corpus passes"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-23T07:00:01Z"
updated = "2026-10-23T07:00:01Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "rule_coverage::every_frob_rule_has_a_corpus passes"
bound = false
+++

Fails on base after a103f44975 removed DOC002 unresolved mdtest cases: 'DOC002 P+ unresolved: missing unresolved case'. Found by YNP04N0.
