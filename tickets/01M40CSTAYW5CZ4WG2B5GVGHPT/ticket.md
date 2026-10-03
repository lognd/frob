+++
id = "01M40CSTAYW5CZ4WG2B5GVGHPT"
title = "gob-cli: per-verb text renderers instead of the generic field dump"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T08:06:31Z"
updated = "2026-10-03T08:06:31Z"
idempotency_key = "m2-gobcli-text-renderers"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-cli/**", "crates/frob/src/release_cmd.rs", "crates/frob/src/milestone_cmd.rs", "crates/frob/tests/**"]

[[acceptance]]
text = "Given release status in text mode, when it runs, then it prints the verdict first and readable sections without duplicated fields, and the JSON has no at_a_glance array"
bound = false
+++

Found on ~2YECX6Q: the generic text renderer prints every data field with keys sorted alphabetically, so release status grew an at_a_glance array duplicating its structured fields to stay readable. Let a verb supply a text renderer (a trait method with the generic dump as default), keep JSON unchanged, migrate release status (drop at_a_glance from the JSON once the renderer exists, a deliberate schema change noted in the CHANGELOG fragment) and milestone show, and follow diagnostics.md 2 for layout (verdict first, then sections, help lines). Agents read JSON, so the text view is free to optimize for people.
