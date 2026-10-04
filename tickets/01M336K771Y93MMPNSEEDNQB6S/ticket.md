+++
id = "01M336K771Y93MMPNSEEDNQB6S"
title = "Bulk-remove T-#### prose citations from docs/modules and docs/strata (T-5134 follow-up)"
type = "docs"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:00Z"
aliases = ["T-5345"]
labels = ["v1-cluster:B3d"]
scope = ["docs/modules/*.md", "docs/strata/*.md", "docs/guides/*.md"]
+++

found while working T-5134: scripts/count_ticket_citations.py --scope docs measured 7215 remaining T-#### prose citations after T-5134's own pass (which cleaned the 24 files that each carried exactly one bare citation). The bulk lives in large modules/strata/guides docs (docs/modules/gates.md alone: 1279) where citations are woven into gate-history narrative prose, not simple asides -- removing them safely needs a slower, section-by-section pass (or a decision to leave narrative-history sections as a declared exemption alongside docs/audits and docs/design/registry), out of scope for T-5134's own budget. Re-run scripts/count_ticket_citations.py --scope docs --list to reproduce the current list.
