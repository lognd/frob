+++
id = "01M5XMJGNF1HWQBEGE31G4B9C1"
title = "Collapse Severity to Error and Unresolved; reject warn/advisory config"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:01Z"
updated = "2026-10-28T12:55:53Z"
labels = ["no-story"]
scope = ["crates/gob-rules/src/**"]

[[acceptance]]
text = "Severity has only Error and Unresolved; Warn and Advisory removed from derive, [rules], fail_on"
bound = false

[[acceptance]]
text = "A config naming warn or advisory is a config error naming error-plus-baseline or off"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.1). Filed from ~ZHW5Y2M.

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
