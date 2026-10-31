+++
id = "01M68811YBPN99TW7VD4RA3JAJ"
title = "Go reflection MethodByName(n).Call is a silent pass in the capability detector"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T05:48:24Z"
updated = "2026-10-31T06:25:06Z"
scope = ["crates/grimble-bind/**", "crates/gob-caps/**", "crates/gob-symbols/**", "crates/gob-ir/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "A Go file calling reflect.ValueOf(v).MethodByName(n).Call reports an Unresolved CAP001 (code.eval or ffi family), never clean"
bound = true

[[acceptance]]
text = "The ignored probe in symbolic_audit.rs is un-ignored and passes"
bound = true
+++

Probe: package m; import "reflect"; func Run(v any, n string) { reflect.ValueOf(v).MethodByName(n).Call(nil) } checks clean today. Found while working ~AH9XAGZ; the probe is an #[ignore]d test in crates/grimble-check/tests/symbolic_audit.rs.
