+++
id = "01M3ZEH464EFCFAZ4XDKE89D5Z"
title = "gob-languages: add Language::Grmb with wildcard arms in the two comment scanners"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T23:17:29Z"
updated = "2026-10-02T23:17:29Z"
idempotency_key = "m2-language-grmb"
labels = ["milestone:2"]
scope = ["crates/gob-languages/**", "crates/gob-directives/src/comments.rs", "crates/frob-obligations/src/comments.rs"]

[[acceptance]]
text = "Given a .grmb path, when detect runs, then Language::Grmb is returned and both scanners compile"
bound = false
+++

From ~63XJMC3 (D-b): adding the variant breaks exhaustive matches in crates/gob-directives/src/comments.rs (segments) and crates/frob-obligations/src/comments.rs (comment_lines); add wildcard arms there, then Language::Grmb with detection by .grmb and the grammar identity from gob_languages::grmb.
