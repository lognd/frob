+++
id = "01M1T07J435JHVVSNHT8T7AZ2T"
title = "r16: path-scoped check judges jsx/ts files too (A-076); size-utility wiring note (A-077)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:42Z"
aliases = ["crunk:T-0131"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/ingest.md", "docs/design/01-customer-requirements.md"]

[[acceptance]]
text = "given the three docs, when read, then path-mode jsx judgment semantics, the full-scan-only boundary, the wiring-note obligation, and CT/E2E ids are stated"
bound = true
+++

Path-scoped check silently drops named tsx/ts files entirely, so an agent trusted a false clean on a file the repo-wide run flags. r16: ingest_paths mirrors the tree walk's jsx and tailwind side for named paths (files matching the jsx globs parse; the self-derived theme always builds), so the per-file TW judgments run in path mode; project-scope rules stay full-scan-only and that boundary is stated. Also records the A-077 doc obligation: document the recommended wiring that exposes a sizes scale as real utility classes.
