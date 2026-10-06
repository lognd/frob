+++
id = "01M47QSFS0VP9DET37MBVCRKXA"
title = "gob-check::sibling: one gob.sibling/1 emitter and parser for every product"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T04:33:15Z"
updated = "2026-10-06T04:33:15Z"
scope = ["crates/gob-check/**", "crates/crunk-check/**", "crates/grimble-check/**", "crates/frob-check/**", "docs/design/sibling-contract.md"]

[[acceptance]]
text = "crunk-check, grimble-check and frob-check build the sibling document only through gob-check::sibling"
bound = false

[[acceptance]]
text = "frob-check parses sibling output through the same module's reader"
bound = false

[[acceptance]]
text = "existing sibling tests and snapshots pass unchanged (byte-identical documents)"
bound = false
+++

products.md section 7 and sibling-contract.md. Move document building (sources, finding records, rules, exceptions, polarity and reason) out of crunk-check/src/sibling.rs, grimble-check/src/sibling.rs and frob-check/src/sibling/doc.rs into gob-check::sibling, emitting from a product-neutral check run; frob-check's merge parses through the same module's typed reader. The JSON schema is generated from those types. Supersedes ~YDDKPEY.
