+++
id = "01M648G0F02C65NHXJAN6J4SDG"
title = "CAP: getattr on a non-module object (self, parameter) is not flagged"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T16:39:37Z"
updated = "2026-10-29T16:39:37Z"
scope = ["crates/gob-symbols/src/canon.rs,crates/grimble-bind/src/caps.rs"]
+++

found while working ~6CV37RW: getattr(obj, n) where obj is not a resolved module is neither a use nor Unresolved.
