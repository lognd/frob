+++
id = "01M4CXSVQQCP2ZJK37Y5GNWGYG"
title = "Type precision on every type-dependent answer (exact, claimed, inferred, dynamic) and Unknown reason classes"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:31Z"
updated = "2026-10-19T12:15:09Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/gob-rules/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a dispatch through an Any-typed receiver, when resolved, then the answer is Unknown with reason dynamic-site and the cheapest remedy"
bound = true
+++

docs/design/cohesion.md 2.1 and 2.3; extends the typed Unresolved reason of ~YR7MCXF.
