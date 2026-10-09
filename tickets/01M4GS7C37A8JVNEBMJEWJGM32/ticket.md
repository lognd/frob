+++
id = "01M4GS7C37A8JVNEBMJEWJGM32"
title = "Engine cache fingerprint uses the executable's size and mtime, so every binary copy or reinstall (global install, landing binary) starts from a cold cache; key it by build identity instead"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T16:51:29Z"
updated = "2026-10-09T17:51:01Z"
scope = ["changelog.d/**", "crates/gob-cache/src/lib.rs", "crates/gob-cache/Cargo.toml"]

[[acceptance]]
text = "Given the same frob build copied to a new path with a new mtime, when frob check runs, then the cache is warm (fingerprint = crate version + git commit + profile + rule registry digest, not exe size/mtime); a rebuild with different code still invalidates"
bound = false
+++

notes/research/profile-2026-10-07.md section 1: the engine fingerprint folds in exe size+mtime; our installs copy binaries into ~/.local/opt/..., so each install and each landing-binary rebuild is a cold cache (CI profile: frob check warm 5.4 s vs cold 221 s).
