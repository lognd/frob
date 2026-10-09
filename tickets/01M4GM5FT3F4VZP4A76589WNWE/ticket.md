+++
id = "01M4GM5FT3F4VZP4A76589WNWE"
title = "Error-flow facts per language: what a unit can raise or return as an error (Rust Result error types exact, Python raise sets May, TS throw Unknown) for impl outcome maps"
type = "story"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T15:23:04Z"
updated = "2026-10-09T15:24:54Z"
labels = ["grimble"]
scope = ["crates/gob-ir/**", "crates/gob-symbols/**", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M4FDAD29CBF7S4EM2FKR5TXQ"

[[acceptance]]
text = "Given Rust fn returning Result<T, PaymentError>, Python def raising PaymentDeclined and calling httpx, and a TS function that throws, when error facts are computed, then Rust yields the enum variants Exact, Python the explicit raises plus callee raises as May, TS Unknown, each with a reason"
bound = false

[[acceptance]]
text = "Given an error set that is not exact, when the facts are consumed by grimble, then the gap surfaces through the existing opaque-cone Unresolved path (no new severity) and an outcome-map declaration on the waypoint is accepted as the claim that resolves it conditionally (D121)"
bound = false
+++

Needed by grmb planning impl outcome maps (variant <- error), checked both ways. Research cycle R2 should survey exception-flow analysis (Java checked exceptions, Python exception analysis tools, Rust) before this is built.
