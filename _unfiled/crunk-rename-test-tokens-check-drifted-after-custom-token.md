+++
id = "01M6Z90S9FW6A6ZNT5RK80RGKN"
title = "crunk rename test: tokens --check drifted after custom token rename (fails on experimental)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T04:28:16Z"
updated = "2026-11-09T04:51:43Z"
scope = ["crates/crunk/**", "crates/crunk-tokens/src/export/**"]

[[acceptance]]
text = "crunk rename followed by tokens --check reports no drift in the regenerated managed exports"
bound = false
+++

found while working KAVWFAE: crates/crunk/tests/rename.rs custom_token_rename_rewrites_definition_aliases_and_every_reference fails at the final 'tokens --check' (status drifted, styles/tokens.css) on base experimental; unrelated to color-mix.
