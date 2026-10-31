+++
id = "01M68ERE6YM5671NGNK7EP55G9"
title = "Go: reflect.Value from tuple returns, range, index and map elements stays silent"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T07:46:02Z"
updated = "2026-10-31T08:45:11Z"
scope = ["crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = 'x, _ := get() with get() (reflect.Value, error), for _, v := range []reflect.Value, vs[0].Call and m["a"].Call on map[string]reflect.Value each report Unresolved code.eval'
bound = false

[[acceptance]]
text = "A clean control with the same shapes over a local type stays clean"
bound = false
+++

found while working ~8H1QZPX: probes of these shapes pass clean.
