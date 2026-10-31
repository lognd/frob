+++
id = "01M6987FAVSB9XGJYWXMHGA5VN"
title = "Grimble spec: audit/fix cycles to convergence with cited research"
type = "task"
category = "in-progress"
priority = "high"
points = 8
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:11:09Z"
updated = "2026-10-31T18:19:43Z"
idempotency_key = "grmb-cohesion-cycles"
scope = ["docs/design/grmb-*.md", "docs/design/README.md", "docs/decisions/**", "notes/research/grmb-corpus/**", "notes/research/grmb-evidence/**", "changelog.d/**", "docs/design/grimble-model.md", "notes/research/README.md", "notes/research/grmb-r1-*.md", "docs/README.md", "notes/README.md", "notes/research/grmb-r2-verification.md"]

[[acceptance]]
text = "Audit/fix cycles on the grimble spec run until a full audit returns zero findings; each cycle is recorded in notes/research/grmb-evidence/cycles.md"
bound = true

[[acceptance]]
text = "Every design change (split/merge/respell) cites at least one primary or vetted secondary source (repo commit/RFC/standard/author with multiple large projects) in notes/research/grmb-evidence/ and a decision in decisions.toml"
bound = true

[[acceptance]]
text = "No docs explosion: spec changes edit existing docs in place (grmb-spec.md, grmb-planning.md); research lands in exactly two new files (notes/research/grmb-evidence/evidence.md and cycles.md, updated per cycle, never one file per cycle or per finding); no new files under docs/design/ except by merging or replacing existing ones; stale or superseded notes and corpus files are deleted or merged, and docs/design/README.md index stays accurate"
bound = true
+++

Follows the fable cohesion audit of node flows, stories and V-model planning. Evidence must come from mined repo history or well-regarded practitioners with multiple large projects.
