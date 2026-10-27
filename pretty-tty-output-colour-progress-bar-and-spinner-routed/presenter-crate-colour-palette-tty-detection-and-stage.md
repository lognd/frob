+++
id = "01M5XMN8GHBCJH7WVMYVXR58J9"
title = "Presenter crate: colour palette, TTY detection and stage progress bar/throbber"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T02:57:31Z"
updated = "2026-10-27T03:52:58Z"
scope = ["crates/frob-present/**", "Cargo.lock", "docs/design/output.md", "changelog.d/01M5XMN8GHBCJH7WVMYVXR58J9.changed.md"]

[[acceptance]]
text = "a presenter crate renders stage progress with a bar or throbber and colour only on a TTY, honours NO_COLOR, and emits nothing extra when piped"
bound = false
+++
