+++
id = "01M4118NGH127F6DGVGS4GVE49"
title = "Remedies as structured data checked against the CLI registry, replacing the source-text scan"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T14:04:09Z"
updated = "2026-10-03T14:04:09Z"
idempotency_key = "m2-remedy-registry"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-cli/**", "crates/gob-diagnostics/**"]

[[acceptance]]
text = "Given every error code, when the remedy test enumerates their structured remedies, then each names an existing verb path and flags"
bound = false
+++

Follow-up of ~992AN0Q: the remedy test scans source literals for frob/grimble spans, so remedies built with format! from runtime pieces and some literal shapes are invisible to it. Make every error code's remedy a structured value (a verb path plus flags plus placeholder arguments, rendered to text by gob-cli), so a test can enumerate them all and check them against Cli::verb_flags() exactly; this also feeds diagnostics.md teaching and the JSON envelope (agents get the command as data). Keep the text scan until the migration is complete.
