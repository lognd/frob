+++
id = "01M6A0VA118026R4EZRRC8VH1W"
title = "Sibling schema Role enum says verifiedby but binding rows serialize verified_by"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T22:21:25Z"
updated = "2026-10-31T22:21:25Z"
idempotency_key = "role-verifiedby-mismatch"
scope = ["crates/gob-check/src/sibling_doc.rs", "crates/grimble-bind/**", "docs/schemas/**"]

[[acceptance]]
text = "A grimble check on a model with a resolving verified_by clause validates against docs/schemas/sibling.json"
bound = false
+++

Found while working PLAN006: grimble check emits role verified_by for a verified_by binding row, but the schema Role enum lists verifiedby, so assert_valid_sibling fails. The PLAN006 test in crates/grimble/tests/graph.rs skips schema validation until this is fixed.
