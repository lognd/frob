+++
id = "01M1T07J45REYJSXWT1B59D3AP"
title = "r17: cache moves out of the repo (A-080)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:42Z"
aliases = ["crunk:T-0133"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/cache.md", "docs/design/01-customer-requirements.md"]

[[acceptance]]
text = "given the three docs, when read, then the cache location rule, the override, the scaffold change, and CT/E2E ids are stated"
bound = true
+++

Every crunk run wrote a cache directory into the adopting repo, tripping their scope gate and getting deleted twice by an agent; the borrower case writes into a tree crunk does not own at all. r17: the result cache lives in the user cache directory keyed by a hash of the resolved project root, overridable via one environment variable; no repo writes, no gitignore management needed; the scaffold stops adding the obsolete ignore line; key semantics and INV-CACHE-01 unchanged.
