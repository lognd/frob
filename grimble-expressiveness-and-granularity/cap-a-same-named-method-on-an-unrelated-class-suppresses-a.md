+++
id = "01M642301PNSE0VTM2F313NY13"
title = "CAP: a same-named method on an unrelated class suppresses a real use elsewhere"
type = "task"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T15:39:02Z"
idempotency_key = "vnvd3q1-decoy"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**", "crates/gob-ir/**", "crates/gob-symbols/**", "crates/grimble-bind/**", "docs/design/binding.md"]

[[acceptance]]
text = "a method defined on a project class never suppresses a use whose receiver resolves to a capability type; test with the decoy in another file"
bound = true

[[acceptance]]
text = "Fix lives in the universal layer (gob-ir/gob-symbols resolution and VocabEntry registry), not a per-language patch in grimble-check; regression test covers every language with an adapter."
bound = true
+++

Case p29 vs p29b: identical uses are reported only when the decoy file is absent. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
