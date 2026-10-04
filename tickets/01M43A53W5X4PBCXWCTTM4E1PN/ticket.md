+++
id = "01M43A53W5X4PBCXWCTTM4E1PN"
title = "Selective v1 ticket import: requirement-bearing open tickets only, history for the rest"
type = "story"
category = "todo"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-04T11:17:59Z"
updated = "2026-10-04T11:17:59Z"
scope = ["crates/gob-dev/src/import_v1.rs", "crates/gob-dev/src/import_v1/**", "docs/migration/**", "docs/design/migration.md"]

[[acceptance]]
text = "Given the v1 ledger, when the importer runs in dry-run mode, then it reports counts per disposition and lists every open ticket it would import with its cluster"
bound = false

[[acceptance]]
text = "Given a v1 ticket in a dropped, built or v1-internal cluster, when the import runs, then it is not imported as open work"
bound = false

[[acceptance]]
text = "Given imported text with a home path or a private term, when it is written, then the redaction rules apply"
bound = false
+++

Owner decision 2026-10-04: import from the v1 ledger only the tickets that carry real requirements, not all 970 open ones (notes/review/v1-gap/B-backlog.md proposes the split; migration.md currently imports everything).

1. Extend the existing v1 importer (gob-dev import-v1-tickets) with a selection: done and dropped v1 tickets import as closed history (outcome preserved, original id as alias, as today); open v1 tickets import as open only if they belong to a requirement-bearing cluster of the B report (statuses DESIGNED and MISSING, plus individually significant tickets it lists), with the cluster recorded as a label (v1-cluster:<id>) and the v1 id as alias; B1 and B2 (system-design and web-app lint) import with the label area:crunk per D88; clusters marked DROPPED-ON-PURPOSE, BUILT and V1-INTERNAL do not import as open (they are listed in the dry-run report with the reason, and optionally import closed as wont-fix history with that reason, if the importer already supports history).
2. The selection is data: a checked-in mapping file (v1 id or cluster to disposition) generated from the B report, reviewed in the PR, not code branches; the dry run prints counts per disposition and every open ticket that would import.
3. Text goes through the ledger write path, so private-term redaction and the home-path rule apply; no absolute paths or private names may enter (fix or strip them).
4. Update migration.md to describe the selective import.
Do NOT run the import against this repository's ledger: produce the dry-run report (counts and the list) and stop; the coordinator reviews it and runs the import.
