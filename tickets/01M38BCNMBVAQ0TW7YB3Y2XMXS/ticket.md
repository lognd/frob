+++
id = "01M38BCNMBVAQ0TW7YB3Y2XMXS"
title = "Docs: ledger tiers -- milestone tier, story flavour, due/rank, TIER001-006 family across tickets docs, ticket-kinds-states guide and vmodel"
type = "docs"
category = "triage"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:00Z"
aliases = ["T-5771"]
labels = ["milestone:v0.536.0", "v1-cluster:B3d"]
scope = ["docs/guides/extending/ticket-kinds-states.md", "docs/strata/vmodel.md", "docs/modules/tickets-data-storage.md", "docs/modules/tickets-lifecycle.md", "docs/modules/tickets.md", "scripts/check_ledger_tiers_doc_drift.py", "tests/gates_suite/test_tier_gate.py"]

[[links]]
kind = "blocked-by"
target = "01M38BCNKNNP946KQM58NCCGXR"

[[links]]
kind = "blocked-by"
target = "01M38BCNKQTNHBMFACZADQ3WKK"
+++

Update docs/modules/tickets-data-storage.md, tickets-lifecycle.md, tickets.md, docs/guides/extending/ticket-kinds-states.md and docs/strata/vmodel.md for the new milestone tier, story flavour, due/rank fields, the TIER001-006 family, --with-ticket, and the retirement of kind: invariant.

Positive control: the repo's doc-edge closure check (frob check doc drift) reports zero drift against the touched code paths.

Doc page: this leaf IS the doc leaf

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

## Unblock log
- 2026-09-24: unblocked by T-draft-3661879e -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-9570bf46 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-58029dd5 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-08ef9199 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-50f4484a -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
