+++
id = "01M6885YYZV2YJ2Z8K119M1TXP"
title = "DEAD001: functions reached only through a May edge stay unresolved despite frob:tests bindings (17 in gob-plan)"
type = "bug"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XMF3XC9ZD6FPZ59ECWJCJ4"
reporter = "lognd"
created = "2026-10-31T05:51:05Z"
updated = "2026-10-31T05:51:05Z"
idempotency_key = "x397svj-may-edge"
scope = ["crates/frob-check-dead/**"]

[[acceptance]]
text = "Given a function reached only through a possible (May) call edge and bound with frob:tests, when frob check runs, then DEAD001 does not report it; the 17 gob-plan cases (field.rs int, count.rs compare, parse/cond.rs shape_inner, print.rs header, emit.rs key and others) report zero findings"
bound = false
+++

Found closing ~X397SVJ. frob:tests bindings and frob:accept DEAD001 do not clear May-edge DEAD001 findings; likely call-graph resolution. Scope glob to be corrected by whoever picks this up (locate the DEAD001 rule crate first).
