+++
id = "01M3ZX779NSRZ97ZQM5DP3BZJZ"
title = "gob-plan crate and GRL lexer: tokens, snippets, strings, regex, comments"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:13Z"
updated = "2026-10-03T05:24:27Z"
idempotency_key = "m2-grl-lex"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/**"]

[[acceptance]]
text = "Given a source with a # comment, a backtick snippet holding $$$ARGS, a double-backtick snippet holding a backtick, a triple-quoted string with common indentation and a /re/i regex, when lexed, then tokens carry gob-text spans, snippet text is raw and the common indent is removed from the block string"
bound = true

[[acceptance]]
text = "Given a non-ASCII identifier or keyword, when lexed, then a located lexical error is returned as a Result and nothing panics"
bound = true
+++

Implements grl-spec.md section 3; plugins.md section 10 (gob-plan).

Create the gob-plan crate (plan format, GRL compiler, executor live here) and its lexer. Snippets are raw text in backticks with only $ special; ASCII-only syntax.
