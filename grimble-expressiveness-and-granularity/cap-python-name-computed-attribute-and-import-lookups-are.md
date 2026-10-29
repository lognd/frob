+++
id = "01M6422ZFEPZJYJQDDM6CV37RW"
title = "CAP: Python name-computed attribute and import lookups are silently accepted"
type = "task"
category = "todo"
priority = "critical"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-29T14:47:38Z"
idempotency_key = "vnvd3q1-py-dynamic-name"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**"]

[[acceptance]]
text = "getattr, __import__, importlib.import_module, vars/__dict__/sys.modules lookups with a non-literal name yield an Unresolved finding; literal names resolve to the origin symbol"
bound = false
+++

Cases p05 p06 p07 p14. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
