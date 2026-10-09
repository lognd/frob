+++
id = "01M4D6NKK3H4V085F2C4A0JHA9"
title = "Dev profile: opt-level 3 for gix-*, zlib-rs, toml and tree-sitter, measured"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:29Z"
updated = "2026-10-09T22:07:34Z"
scope = ["changelog.d/**", "Cargo.toml"]

[[acceptance]]
text = "Given the change, when measured, then debug ticket doable cold drops and the clean-compile delta is recorded"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 11; record clean-compile cost and the debug ticket doable cold time before and after in build-test-ci.md 5.
