+++
id = "01M4MMGDBXRGC9X90CZPPSKN6Z"
title = "typos: the docs spelling job fails on 'wheres' (plural of a GRL where clause) in gob-plan lowering"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T04:46:00Z"
updated = "2026-10-11T13:42:52Z"
scope = ["typos.toml", "docs/crunk/rules/README.md", "crates/frob/src/profile_cmd.rs", "crates/frob/tests/profile.rs", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "the pinned typos 1.50.3 run over the repository exits 0, while a genuine misspelling still fails"
bound = true
+++

found after pushing bc9b9cf2f: CI docs (spelling) exits 2 on crates/gob-plan/src/lower/convert.rs lines 101,123,196,197 and emit.rs 236 (wheres should be whereas). wheres is the plural of GRL's where clause, a domain term. Add it to the reviewed extend-words list with the reason. This red job blocks every frob land (E-LAND-BASE-RED).
