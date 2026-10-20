+++
id = "01M4839B5ZG4ZYPVXKYMKG678C"
title = "Drop dependencies crunk-check no longer uses after the sibling move"
type = "chore"
category = "todo"
priority = "low"
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T07:54:09Z"
updated = "2026-10-06T10:21:34Z"
scope = ["crates/crunk-check/Cargo.toml", "Cargo.lock"]
+++

~BVCRKXA moved sibling building into gob-check; crunk-check may no longer use gob-diagnostics and gob-text. Remove what is unused (cargo-shear in ~19X37CZ will gate this class later).
