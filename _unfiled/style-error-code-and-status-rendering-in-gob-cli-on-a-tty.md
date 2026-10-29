+++
id = "01M62W1RDJQXY7GD8CW13J001Y"
title = "Style error[CODE] and status rendering in gob-cli on a TTY"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T03:42:52Z"
updated = "2026-10-29T05:47:08Z"
scope = ["crates/gob-cli/**"]
+++

Found while working ~W1GQTPG: error layout (render.rs failure) and the generic value_lines text fallback live in gob-cli and are still plain. Colour via frob-present palette, NO_COLOR safe, exit codes unchanged.
