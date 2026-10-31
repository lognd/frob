+++
id = "01M68A4X3WSCGTN070S8H1QZPX"
title = "Go reflect.Value held in a typed parameter or field calls Call/MethodByName silently"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T06:25:28Z"
updated = "2026-10-31T07:46:06Z"
scope = ["crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs", "changelog.d"]

[[acceptance]]
text = "func Run(m reflect.Value) { m.Call(nil) } and a struct field of type reflect.Value called via s.m.Call report an Unresolved code.eval, never clean"
bound = true

[[acceptance]]
text = "A clean control (a parameter of a locally declared type named Value) stays clean"
bound = false
+++

Found while working ~4RA3JAJ. go_uses types only calls to reflect APIs as reflect.Value; a parameter, field or return value DECLARED as reflect.Value is a Shadow and resolves to nothing, so the dispatch passes clean. Fix by resolving declared types through the import (symbolic), not by text.
