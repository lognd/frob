+++
id = "01M408FXDQNHMQSA4RF2HHBFSY"
title = "universal-model.md and cli.md: four required Unresolved cases (tool-failed added)"
type = "docs"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T06:51:12Z"
updated = "2026-10-03T06:51:12Z"
idempotency_key = "m2-required-cases-four"
labels = ["milestone:2", "good-first"]
scope = ["docs/design/universal-model.md", "docs/design/cli.md"]

[[acceptance]]
text = "Given universal-model.md and cli.md, when read, then four required cases are listed including tool_failed"
bound = false
+++

Follow-up of ~APQCEPT. ## Start here
RequiredReason gained ToolFailed { stage } (crates/gob-rules/src/required.rs). docs/design/universal-model.md (around line 293, 'one of the three required cases') and cli.md still say three: update both to list sibling_missing, annotation_required, zero_subjects and tool_failed, with one line on tool_failed (a configured tool stage that could not run, exited abnormally, or printed output its parser cannot read). Test: frob check --ticket passes. Ask the coordinator if unsure.
