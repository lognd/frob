+++
id = "01M4DPRRJWQGW5Q2GHC2YABCF4"
title = "GRL: header needs becomes capabilities and side relations move to reads (parser, printer, spec, GRL014 goldens)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-08T12:10:50Z"
updated = "2026-10-08T12:10:50Z"
scope = ["crates/gob-plan/src/grl/parse/rule.rs", "docs/design/grl-spec.md", "crates/gob-plan/tests/grl_errors/cases/GRL014.*"]
+++

found while working ~ZKM5W7Y. Formal review 2026-10-08 section 4 item 7. GRL014 and its golden currently say needs diff; moving side relations to a reads header changes the golden, the printer and the spec together. Left out of ZKM5W7Y because the existing golden fixes the needs wording.
