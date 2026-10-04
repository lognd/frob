+++
id = "01M43HGBQ9YS0Z8YPKQ41MBK6Q"
title = "TOML comment scanner reads # inside multi-line strings as comments, so quoted directives fire"
type = "bug"
category = "in-progress"
priority = "critical"
reporter = "lognd"
created = "2026-10-04T13:26:27Z"
updated = "2026-10-04T13:56:20Z"
scope = ["crates/frob-obligations/src/comments.rs", "crates/gob-directives/src/comments.rs", "crates/gob-languages/src/hash.rs", "crates/gob-languages/src/lib.rs"]

[[acceptance]]
text = "Given a TOML file whose multi-line string contains a line starting with # frob:doc, when frob check runs, then no directive is read from it"
bound = true

[[acceptance]]
text = "Given the current ledger on experimental, when frob check runs, then no DRIFT002 or TEST001 finding points into tickets/"
bound = true
+++

The v1 import (41e686bce) put ticket text quoting v1 code into tickets/*/events/*.toml multi-line strings, e.g. a line that quotes "# frob:doc docs/modules/...md#...". frob check now reports DRIFT002 (2) and TEST001 (1) errors on those event files: the comment scanner for TOML treats a # inside a multi-line basic or literal string as a comment start, so text that merely quotes a directive is evaluated as one. Fix structurally: the TOML comment scanner must lex strings (basic, literal, multi-line basic with escapes, multi-line literal) and only report real comments; audit the other comment scanners in gob-languages and gob-directives for the same class of bug (string-blind # or // detection) and fix or ticket each. Add a table or property test covering every string form.
