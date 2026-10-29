+++
id = "01M62W1RDJQXY7GD8CW13J001Y"
title = "Style error[CODE] and status rendering in gob-cli on a TTY"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T03:42:52Z"
updated = "2026-10-29T05:47:15Z"
scope = ["crates/gob-cli/**"]

[[acceptance]]
text = "Given a TTY with colour enabled, when a gob-cli failure renders, then the error CODE and status are styled; given NO_COLOR or a non-TTY the output is byte-identical to today and exit codes are unchanged"
bound = false
+++

Found while working ~W1GQTPG: error layout (render.rs failure) and the generic value_lines text fallback live in gob-cli and are still plain. Colour via frob-present palette, NO_COLOR safe, exit codes unchanged.
