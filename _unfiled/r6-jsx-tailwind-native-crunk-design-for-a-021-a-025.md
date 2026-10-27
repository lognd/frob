+++
id = "01M1QDTV1VBYG7Y76JZ97YCMH3"
title = "r6: JSX/Tailwind-native crunk -- design for A-021..A-025"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:34Z"
aliases = ["crunk:T-0059"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given A-021..A-025, when the design tree is read, then each maps to a CR/CT and concrete layer-2..4 contract changes with disjoint implementation-wave scopes"
bound = true
+++

High-level trial feedback: crunk reads only .css while the codebase keeps design values in className strings, inline style props, and tailwind.config.ts, so it checks but does not shape development. r6 adds CR-17..CR-21: JSX+Tailwind ingestion and rules (A-021/A-018/A-019), TSX component inventory (A-022), Tailwind theme generation from crunk.toml (A-023), CI-grade check --report with a stable schema (A-024), and a utility-first org model (A-025).
