+++
id = "01M1T07J3NDYGGQAAGGQ07GP8S"
title = "r12: className-expression scanning rule (A-060 template literals, clsx/cn)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:03Z"
aliases = ["crunk:T-0117"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/subsystems/ingest.md", "docs/design/02-specification.md"]

[[acceptance]]
text = "given ingest.md and 02-specification.md, when read, then they state the static-segment scanning rule, the boundary-token drop, and the UT/CT ids for it"
bound = true
+++

The adopting project's Shell.tsx mobile-nav dropdown consumes z-footer inside a template-literal className with interpolation; the scanner skipped the whole template so unused_tokens reported a false dead layer. r12 rule: inside a className expression every string-literal fragment and template-literal static segment is a utility-candidate list; tokens touching an interpolation boundary are dropped; .ts template constants get the same static-segment scan. Covers clsx/cn helper-call literals for free.
