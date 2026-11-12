+++
id = "01M778EENHT3NQ80WZRG76M9WS"
title = "indexgen: allow clippy::too_many_lines on generated bind()"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-12T06:52:11Z"
updated = "2026-11-12T06:52:11Z"
scope = ["crates/gob-rules/src/indexgen.rs"]
+++

found while working ~WM2DDBN: crunk-rules bind() is now 101 lines and trips clippy::too_many_lines; generated mod.rs cannot carry a hand allow
