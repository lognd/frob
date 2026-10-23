+++
id = "01M1QDTV1BZRB15ERAWYTE22KQ"
title = "reconcile held r4 doc text with landed wave-1 doc edits"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:03Z"
aliases = ["crunk:T-0043"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/spec.md", "docs/design/subsystems/tokens.md", "docs/design/subsystems/rules.md", "docs/design/subsystems/report.md", "docs/design/subsystems/shell.md", "docs/index.md"]

[[acceptance]]
text = "given the stash 'r4 docs held for wave-1 lease reconciliation', when it is merged and committed, then the r4 design content for waves 2-4 is present in HEAD alongside wave-1's landed doc text and the stash entry is dropped"
bound = true
+++

T-0040 held five leased docs (plus 02 and index) in a stash while wave 1 ran; this merges that r4 text with the wave-1 agents' landed doc edits: r4 sections that describe waves 2-4 (stacks, ORG005, entry, cache, query) join the now-present-tense wave-1 sections.
