+++
id = "01M5XNNJF27AX6510KBK4EMP90"
title = "Detector registry row: precision, cwe, rationale, safer alternative, severity; consult per-atom severity in CAP001"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:09Z"
updated = "2026-10-27T03:15:09Z"
idempotency_key = "grimble-expr-rowschema-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/gob-ir/src/registry.rs", "crates/grimble-bind/src/caps.rs", "crates/gob-packs/src/tier1/**", "crates/grimble-model/src/model.rs"]

[[acceptance]]
text = "CAP001 severity comes from the atom row or [packs.severity] override, with a test for a warn-level atom"
bound = false

[[acceptance]]
text = "CAP001 messages include the atom rationale and safer alternative when the row has them"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. grimble-model.md 9.6 specifies the row `{atom, language, detector_kind, pattern_or_vocab_ref, precision, cwe, rationale, safer_alternative, severity}`; AtomEntry/DetectorEntry (registry.rs:33-50) carry only name, aliases, lang and kind. caps.rs:17-18 'the pack severity table is not consulted (CAP001 is an Error, CAP002 a Warning)', so incidental atoms cannot be Warn and repos cannot tune per atom. Extend the row, surface rationale and safer alternative in CAP001 messages, and honour [packs.severity].
