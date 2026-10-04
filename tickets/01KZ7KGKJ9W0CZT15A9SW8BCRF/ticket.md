+++
id = "01KZ7KGKJ9W0CZT15A9SW8BCRF"
title = "Tail-end repo hygiene: docs completeness, detector-gap audit, vestigial cleanup, waiver audit"
type = "epic"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-08-05T00:00:00Z"
updated = "2026-08-05T00:00:00Z"
aliases = ["T-1609"]
labels = ["milestone:1.1.0", "v1-cluster:F1"]
scope = ["docs/**", "src/frob/**", "tests/**"]

[[links]]
kind = "blocked-by"
target = "01KZ7KGKHXGS6W2YAVRY27W0D5"
+++

Work to run only AFTER the rest of the queue is drained, in the stated order. Filed now so it is not forgotten, deliberately gated so it is not started early.

Why the gating is real and not ceremony: each child measures the repo's finished state. A docs sweep run mid-drive documents code that is about to change; a vestigial-artifact cleanup run mid-drive deletes things an in-flight ticket still references; a waiver audit run mid-drive judges waivers whose follow-up work has not happened yet and would condemn honest ones. Running these early produces confidently wrong answers -- the most expensive kind.

Order: docs sweep, then the detector-gap audit it feeds, then the artifact cleanup, and the waiver audit LAST, as explicitly requested.
