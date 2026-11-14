+++
id = "01M7AV6DCR4Z15F1G4NSKSTFYN"
title = "release criteria: add an evidence provider for ticket state and CI so exit criteria bind"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:17:34Z"
updated = "2026-11-14T00:01:47Z"
labels = ["no-story"]
scope = ["crates/frob-release/**"]

[[acceptance]]
text = "Each 0.533.0 criterion binds to evidence and attestation can verify."
bound = false
+++

H2: no verb or provider binds the 7 exit criteria; attesters config does not match the commit author identity so attestation is dead; one criterion is circular. Source: frob-audit-meta.md (Opus audit).
