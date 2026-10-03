+++
id = "01M3ZX7FPXFVAXEF6QJCFZ0A54"
title = "Pack tree digest: blake3 Merkle over every byte of a pack"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:22Z"
updated = "2026-10-03T03:34:22Z"
idempotency_key = "m2-sec-tree-digest"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-packs/src/digest/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[acceptance]]
text = "Given a pack directory, when a documentation-only file changes, then the tree digest changes; when the executable bit changes, it changes too"
bound = false

[[acceptance]]
text = "Given a symlink, hardlink, device file or path escaping the root inside a pack, when digested, then PACK005 is returned and no digest is produced"
bound = false
+++

Implements security.md section 2.1 (I3).

Normalized relative path, file type, executable bit, exact bytes of every file including manifest, GRL, WASM, data and explain text, plus digests of included packs. Symlinks, hardlinks, device files and escaping paths are PACK005.
