+++
id = "01M648G0HAPTHCHX4BKCFHG5QT"
title = "CAP: TS static import default/namespace direct calls not emitted by path_uses"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T16:39:37Z"
updated = "2026-10-29T16:39:37Z"
scope = ["crates/gob-symbols/src/lookups.rs"]
+++

found while working ~6CV37RW: import cp from 'x'; cp.exec() is not emitted as a path use.
