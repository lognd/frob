+++
id = "01M6422ZFEPZJYJQDDM6CV37RW"
title = "CAP: Python name-computed attribute and import lookups are silently accepted"
type = "task"
category = "in-progress"
priority = "critical"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-29T16:00:55Z"
idempotency_key = "vnvd3q1-py-dynamic-name"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**", "crates/gob-ir/**"]

[[acceptance]]
text = "getattr, __import__, importlib.import_module, vars/__dict__/sys.modules lookups with a non-literal name yield an Unresolved finding; literal names resolve to the origin symbol"
bound = false

[[acceptance]]
text = 'a literal name argument (Python __import__("os"), getattr(os, "system"), importlib.import_module("os"); JS require("child_process"), import("x"), obj["k"]; C# Type.GetType("..."); same for every supported language) resolves to the origin symbol exactly as the direct form would, tested per language; only non-literal names yield Unresolved'
bound = false

[[acceptance]]
text = "Literal-name resolution is implemented once in the shared gob-ir const_value capability and consumed by every language adapter in gob-symbols; no per-language lexical special case in grimble-check. Non-literal names return Unknown/Unresolved."
bound = false
+++

Cases p05 p06 p07 p14. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
