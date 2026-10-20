+++
id = "01M43JNVX9P9H6WMGZS6MTDY4R"
title = "Rust plain-text comment fallbacks and bind.rs hash-block heuristics are string-blind"
type = "bug"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-04T13:46:56Z"
updated = "2026-10-04T13:46:56Z"
+++

found while working ~41MBK6Q: rust_plain (no-tree fallback in gob-directives comments) finds /* regions without lexing strings; bind.rs block_limit and is_trailing treat any line starting with # as a comment in TOML/YAML even inside multi-line strings. Fallback-only or binding-only, lower risk.
