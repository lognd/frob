+++
id = "01M5NQHBT2GVXS9EEXBMJZYWH9"
title = "CI rust (ubuntu) job red: 34 failing tests on experimental (frob-cli it, gob-packs, frob-check, docgen, crunk)"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-24T01:13:53Z"
updated = "2026-10-24T03:08:31Z"
scope = ["crates/frob/**", "crates/gob-cli/**", "crates/grimble-ci/**", "docs/design/cli.md", "docs/**", "crates/grimble/**", "crates/gob-git/**", "crates/gob-packs/**", "crates/frob-check/**", "crates/gob-mdtest/**", "crates/frob-docgen/**", "crates/crunk/**", "crates/crunk-ingest/**", "crates/grimble-check/**", "crates/frob-obligations/tests/mdtest/**", "Cargo.lock"]

[[acceptance]]
text = "Given experimental at HEAD, when the rust (ubuntu-latest) CI job runs cargo nextest, then none of the tests listed in the ticket body fail"
bound = false
+++

Failing list from run 40044678089 job 120723671777 saved in the session scratchpad failing.txt
