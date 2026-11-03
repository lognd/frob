+++
id = "01M6GEY2ZNBK1CRPSDQ3NFJCSC"
title = "VET001/VET003 zero subjects when base has no new deps"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-11-03T10:23:03Z"
updated = "2026-11-03T11:50:08Z"
scope = ["crates/grimble-vet/**"]

[[acceptance]]
text = "Given a lock identical to the base ref, when grimble vet runs with a base, then VET001-003 are not-applicable rather than examining zero subjects"
bound = true
+++
