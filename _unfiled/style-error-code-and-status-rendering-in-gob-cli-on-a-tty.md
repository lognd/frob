+++
id = "01M62W1RDJQXY7GD8CW13J001Y"
title = "Style error[CODE] and status rendering in gob-cli on a TTY"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T03:42:52Z"
updated = "2026-10-29T06:28:03Z"
scope = ["crates/gob-cli/**", "docs/design/output.md"]

[[acceptance]]
text = "Given a TTY with colour enabled, when a gob-cli failure renders, then the error CODE and status are styled; given NO_COLOR or a non-TTY the output is byte-identical to today and exit codes are unchanged"
bound = true
+++

Found while working ~W1GQTPG: error layout (render.rs failure) and the generic value_lines text fallback live in gob-cli and are still plain. Colour via frob-present palette, NO_COLOR safe, exit codes unchanged.
