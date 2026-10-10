+++
id = "01M4H408PG9RR728AQGGRETKJ3"
title = "Standalone grimble check does not run the CAP rules (CAP001/CAP002); only frob check hosting grimble does, so grimble alone reports a clean model that frob rejects"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T19:59:50Z"
updated = "2026-10-10T20:39:28Z"
labels = ["grimble"]
scope = ["crates/grimble/**", "crates/grimble-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given a model node using exec with no grant, when grimble check runs standalone, then CAP001 fires exactly as under frob check, and the rule list is identical in both hosts"
bound = true
+++

Found by ~5357VS8's implementer 2026-10-09: grimble check returned no findings while frob check reported 6 CAP001 errors on the same model. Violates sibling-contract.md (the standalone product applies its own rules).
