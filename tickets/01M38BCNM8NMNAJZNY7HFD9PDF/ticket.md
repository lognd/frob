+++
id = "01M38BCNM8NMNAJZNY7HFD9PDF"
title = "Review verdict as ticket evidence + strata verification node"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-09T20:42:08Z"
aliases = ["T-5768"]
labels = ["v1-cluster:B3d", "triage:accepted"]
scope = ["src/frob/tickets/_evidence.py", "tests/system/test_cli_evidence_enforcement.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M38BCNM7VWPGK41BXPGC5XVM"
+++

Review verdict as ticket evidence (existing --evidence-cmd wiring only, no new machinery) plus a strata verification node at customer-test level in docs/strata/vmodel.md.

Positive control: a ticket bound to a LAYOUT-gated story with an --evidence-cmd pointing at frob gallery verify shows the verdict in frob ticket show; a stale verdict blocks frob check --ticket.

Doc page: docs/strata/vmodel.md#layout-verification-node

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
