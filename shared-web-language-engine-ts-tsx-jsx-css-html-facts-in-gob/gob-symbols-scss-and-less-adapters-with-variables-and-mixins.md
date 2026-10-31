+++
id = "01M487BKN1FE92BQ72KQWGBG11"
title = "gob-symbols: SCSS and Less adapters with variables and mixins as phase"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T09:05:18Z"
updated = "2026-10-31T10:29:30Z"
labels = ["creates:crates/gob-symbols/src/scss/**", "no-story"]
scope = ["crates/gob-symbols/src/scss/**", "crates/gob-languages/**", "crates/gob-symbols/src/lib.rs"]
+++

found while working ~Z8V73JM: the CSS adapter models plain CSS only. D96 (docs/design/language-engines.md sections 2-3) makes SCSS variables and mixins phase terms; needs an scss grammar in gob-languages and the expand capability.

no-story: internal engineering task in gob-symbols; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
