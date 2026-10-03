+++
id = "01M3ZTVKT99TVVVEKSKAMBGYQ4"
title = "Navigation design: canonical ids only, verifiable reindex, generated docs, profiles and a repository tour"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:52:56Z"
updated = "2026-10-03T02:56:41Z"
idempotency_key = "m2-navigation-design"
labels = ["milestone:2"]
scope = ["docs/design/**", "notes/research/docs-survey.md"]

[[acceptance]]
text = "Given navigation.md, when read, then the canonical-id enforcement, the reindex commit and its replay check, the generated set with markers and gates, profiles, good-first support and the repository tour are specified, and tickets.md and mirror.md agree on the layout"
bound = false
+++

Owner decisions 2026-10-04 on the documentation survey (notes/research/docs-survey.md): commit generated pages in the code repository, marked and checked; ticket files move when their epic changes, but only in a reindex commit that is checkable as nothing but a reindex, and paths must never be used as references (enforce canonical ids); indexes written inline by default with a CI option; the code repository pointer is a README section; docs/architecture.md linked from the top of README and CONTRIBUTING; newcomer and experienced guides, possibly profiles; strong support for newcomers picking something small; a small generated tutorial or walkthrough that teaches a newcomer how the repository works; SUMMARY.md generated from an order file. Write docs/design/navigation.md (D81), reconcile tickets.md section 2 (machine layout) with the branch layout of mirror.md, note in documentation.md why frob commits generated pages, add the survey to notes/research.
