+++
id = "01M44YYN4E7SXWHQB3H7EHD37P"
title = "frob migrate: consumer repositories from v1 to v2 (migration.md section 1)"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-05T02:40:42Z"
updated = "2026-10-05T02:40:42Z"
+++

The consumer migration verbs designed in docs/design/migration.md section 1 are not built (frob migrate is an unknown subcommand). Needed by the project-hullbreach migrations (~P2H17KX, ~WR4MGKG) and every other v1 fleet repository. The ticket importer that already exists for this repository (gob-dev import-v1-tickets with the selection mapping, ~TM4EN1PN lineage) is the starting point for migrate tickets; reuse it rather than writing a second importer. frob.lock re-emission stays gated on the final digest scheme per migration.md.
