+++
id = "01M4Q3A2SA49G06ZVAN753TYM2"
title = "Design A: FileReader trait in gob-walk (gob-git implements), callers take an injected reader"
type = "task"
category = "in-progress"
priority = "high"
points = 8
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-12T03:43:10Z"
updated = "2026-10-21T14:07:21Z"
scope = ["crates/gob-walk/**", "crates/gob-git/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4CTE0GYDX0XW64JRNF2ZMQG"

[[acceptance]]
text = "Given gob-walk, when built, then it defines a FileReader trait and has no gob-git dependency"
bound = true

[[acceptance]]
text = "Given gob-git, when built, then it implements FileReader and a fake reader in a gob-walk test drives a walk"
bound = true
+++

Decision (design A, injected reader; registry rejected for hidden global state). Stage 1: trait in gob-walk, gob-git impl, gob-lock->gob-ir and gob-cache->gob-exec edges dropped (~NF2ZMQG). Stage 2: convert callers crate by crate (~5A9VYZQ: ~30 fs::read sites, 5 crates, frob-obligations). The gix-free cargo metadata test lands once callers are converted. Replace the full-suite criteria with scoped crate nextest runs (full suite needs ~12 GB). Design only: not implemented.
