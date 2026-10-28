+++
id = "01M5XMN90BZAYHQSK214270F1C"
title = "Route all human output through logging; ban println in verb code"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T02:57:31Z"
updated = "2026-10-28T12:55:41Z"
labels = ["no-story"]
scope = ["crates/frob/src/**"]

[[acceptance]]
text = "a policy rule fails println/eprintln in verb code outside the presenter; existing call sites are routed through logging"
bound = false
+++

no-story: internal engineering task in frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
