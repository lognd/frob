+++
id = "01M4D6NJZYKMD1J9PSFE4GA6NV"
title = "gob-symbols: stop re-parsing Rust macro bodies with a second tree-sitter pass"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:29Z"
updated = "2026-10-08T07:29:29Z"
scope = ["changelog.d/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given the Rust corpus, when parsed, then outputs are unchanged and the nested parse is gone"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 10 (rust.rs:1838; 35-43 percent of any parse).
