+++
id = "01M68EREAH73HNXY2YJ6Q0NEFG"
title = "Go: reflect.Value from method results and embedded fields stays silent"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T07:46:02Z"
updated = "2026-10-31T09:46:12Z"
scope = ["crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "s.get().Call where get is a method returning reflect.Value, and s.Call where S embeds reflect.Value, report Unresolved code.eval"
bound = false

[[acceptance]]
text = "A clean control over a locally declared Value type stays clean"
bound = false
+++

found while working ~8H1QZPX: probes of these shapes pass clean.
