+++
id = "01M7FRSNWMA6PNZNTGN68R6BZJ"
title = "land/check: stale shared cargo target yields misleading TOOL001 (truncated compile error)"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T14:11:51Z"
updated = "2026-11-15T14:11:51Z"
idempotency_key = "gap-stale-shared-target"

[[acceptance]]
text = "Given a stale artifact in the shared cargo target, when a tool stage fails to compile, then the finding names the target dir and the clean remedy and shows the first compile error, not only the tail"
bound = false
+++

0MD95W3 hit E0422/E0609 from stale gob-lock rlib in .git/frob/cargo-target/<toolchain>; mtime-normalized worktrees reuse fingerprints. Clean the failing crates in the ambient CARGO_TARGET_DIR, not the checkout target.
