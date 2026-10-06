+++
id = "01M47Y1QAY9FZYADME4RRKWM9R"
title = "Run clippy-windows in land/evidence so unix-only helper misuse cannot land"
type = "task"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T06:22:33Z"
updated = "2026-10-06T11:41:26Z"
scope = ["crates/gob-dev/src/ci.rs"]
+++

Follow-up to ~G436171. Proposal: add a cross-target clippy gate (cargo clippy --workspace --all-targets --target x86_64-pc-windows-msvc, i.e. the clippy-windows step of cargo dev ci) to the standard evidence ref used by implementers (append '&& cargo dev ci --step clippy-windows' via a goway-run wrapper) and make the land verb run 'cargo dev ci --step clippy-windows' on the merged tree through goway before fast-forwarding experimental, failing land on non-zero. Cheaper alternative: add clippy-windows to the default 'cargo dev ci' step list if absent so the documented whole-workspace remote command already covers it.
