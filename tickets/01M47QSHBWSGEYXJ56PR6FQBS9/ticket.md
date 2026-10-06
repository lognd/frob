+++
id = "01M47QSHBWSGEYXJ56PR6FQBS9"
title = "frob check and doctor through the Product trait"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T04:33:17Z"
updated = "2026-10-06T08:30:03Z"
scope = ["crates/frob-cli/**", "crates/frob-check/**", "crates/frob/**", "crates/gob-product/**", "crates/crunk/**", "crates/grimble/**"]

[[links]]
kind = "blocked-by"
target = "01M47QSGHYD2EQ4552V1B4EEQZ"

[[acceptance]]
text = "frob check and frob doctor run through gob-product"
bound = true

[[acceptance]]
text = "frob CLI snapshot and verb tests pass unchanged"
bound = true
+++

products.md section 7. frob-cli's check and doctor verbs instantiate gob-product's generic verbs with a frob Product impl; frob's other verbs stay frob's. Behaviour and output unchanged.
