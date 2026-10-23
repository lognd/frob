+++
id = "01M1QDTV0ZT3DSJYC6M45NRVMS"
title = "r4: fold APROBLEMS field findings and query/cache requirements into design tree"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:04Z"
aliases = ["crunk:T-0031"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/**/*.md", "invariants/*.md", "docs/index.md", "docs/design/*.md", ".gitignore"]

[[acceptance]]
text = "given the APROBLEMS findings, when the design tree is read, then every finding maps to a CR/CT and a layer-2..4 contract change"
bound = true
+++

Field trial findings A-001..A-008 from ../logand.app-v2/APROBLEMS.md plus new customer requirements (queryability, content-addressed caching) become CR-09..CR-16 and propagate down: 02 spec (CLI, schema, catalog ORG005, E2E-10..17), 03 system (cache subsystem, INT-09/10, r4 log), subsystem contracts, new cache.md.
