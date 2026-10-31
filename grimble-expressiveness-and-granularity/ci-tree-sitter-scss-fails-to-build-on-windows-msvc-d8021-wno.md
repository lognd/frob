+++
id = "01M692F18RSTN608B6QK8C57DZ"
title = "CI: tree-sitter-scss fails to build on windows MSVC (D8021 /Wno-unused-parameter)"
type = "bug"
category = "todo"
priority = "critical"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T13:30:25Z"
updated = "2026-10-31T13:30:25Z"
idempotency_key = "ci-scss-msvc-1"
scope = ["crates/gob-languages/**", "Cargo.toml", ".cargo/**"]

[[acceptance]]
text = "cargo build -p gob-languages succeeds on windows-latest with the scss feature enabled"
bound = false
+++

cc-rs passes GCC flag /Wno-unused-parameter to cl.exe via tree-sitter-scss 1.0.0 build.rs. Fix by patching/vendoring the grammar or CFLAGS handling; verify on windows CI.
