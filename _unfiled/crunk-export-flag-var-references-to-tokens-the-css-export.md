+++
id = "01M7EXS945HV88DDHQ5CGGZ5PD"
title = "crunk export: flag var() references to tokens the css export does not define"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK8FEAC1T9J0XMDFWKG0Y"
reporter = "lognd"
created = "2026-11-15T06:19:47Z"
updated = "2026-11-15T06:19:47Z"
idempotency_key = "crunkplan-90737333c989"
labels = ["no-story"]

[[acceptance]]
text = "a var() pointing at an unexported token produces a finding"
bound = false

[[acceptance]]
text = "a var() to an exported token produces none"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H3.
Evidence: var(--x) may reference a token the css export omits
Remedy: cross-check var() uses against exported custom properties
Crates/files: crates/crunk-export, crates/crunk-rules
Verify against HEAD first; the audit ran on a stale binary.
