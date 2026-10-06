+++
id = "01M48FXB2PXX2FBXFKCFWSQYH1"
title = "crunk-check: first web rule over markup, style and class_tokens (className tokens against CSS declarations and custom properties)"
type = "task"
category = "in-progress"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:48Z"
updated = "2026-10-06T13:00:49Z"
scope = ["crates/crunk-check/**", "crates/frob/tests/web_conformance.rs", "changelog.d/01M48FXB2PXX2FBXFKCFWSQYH1.added.md", "crates/gob-mdtest/coverage-allowlist.toml", "Cargo.lock"]

[[acceptance]]
text = "Given a CSS declaration or TSX style prop with a colour literal outside the palette, when crunk check runs, then COLOR001 fires naming the nearest palette token"
bound = true

[[acceptance]]
text = "Given a palette colour, a translucent variant of an opaque palette colour, a var() token reference or a non-colour keyword, when checked, then COLOR001 is clean"
bound = true

[[acceptance]]
text = "Given the shared web fixture with the default preset, when crunk check runs, then its rules list carries COLOR001 and it reports the off-palette CSS and TSX literals"
bound = true
+++

crunk check runs over the shared TSX/CSS fixture with an empty rule list (crates/frob/tests/web_conformance.rs asserts rules == []). The first rule should read gob_ir markup/style and class tokens, and replace that assertion. Found while working ~4M1BX5H.
