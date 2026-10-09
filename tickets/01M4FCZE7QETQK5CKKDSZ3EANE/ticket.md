+++
id = "01M4FCZE7QETQK5CKKDSZ3EANE"
title = "Directive parser rejects trailing foreign pragmas after a directive (# noqa: E501, // eslint-disable-line, # type: ignore) with PARSE001"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T03:58:12Z"
updated = "2026-10-09T05:27:13Z"
labels = ["adoption:hullbreach", "creates:crates/gob-directives/tests/mdtest/trailing-pragma.md"]
scope = ["changelog.d/**", "crates/gob-directives/src/lex.rs", "crates/gob-directives/tests/mdtest/trailing-pragma.md"]

[[acceptance]]
text = "Given frob:todo or frob:tests followed by a trailing # noqa, // eslint-disable-line or # type: ignore[...] pragma, when directives are parsed, then the pragma is ignored and the directive parses with its key=value args intact"
bound = false
+++

Hullbreach platform: 88 sites mix note= with a trailing noqa. Foreign tool pragmas on the same comment line end the directive's argument list.
