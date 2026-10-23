+++
id = "01M1QDTV1GTS9QZCSW8KB3RM82"
title = "r5: second-trial APROBLEMS findings A-009..A-016 into the design tree"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:03Z"
aliases = ["crunk:T-0048"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given APROBLEMS A-009..A-016, when the design tree is read, then each finding maps to a CT and a concrete layer-2..4 contract change"
bound = true
+++

Second field trial (logand.app-v2, crunk at e1ddc50) verified A-001..A-007 fixed and filed A-009..A-016: schema-error detail hidden behind -v, documented defaults actually required, tokens --format css writes instead of previewing, dry-run message reads as success with unfixable errors remaining, ORG005 message carries absolute paths, per-role contrast floors (WCAG large-text exception), query-never-fails documentation, tokens header passthrough + quoted family names. All trace to existing CR-01/02/04/05/06; this revision propagates them through layers 1-4.
