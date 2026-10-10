+++
id = "01M4HQEPMTPBQ9H4MH0B93F0TP"
title = "experimental CI red: clippy-windows fails on unused variable 'shared' in frob-land ratchet.rs share_build_dir (symlink code is unix-only), from ~DWRJEZV"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
points = 1
reporter = "lognd"
created = "2026-10-10T01:39:46Z"
updated = "2026-10-10T01:57:56Z"
scope = ["crates/frob-land/src/ratchet.rs", "changelog.d/**"]

[[acceptance]]
text = "Given the Windows clippy job, when cargo dev ci runs clippy-windows, then frob-land compiles with -D warnings (the canonical-path binding is cfg-gated with the unix symlink code or used on both targets)"
bound = true
+++

CI run 38013006212 (c1731c380): clippy-windows error: unused variable shared at crates/frob-land/src/ratchet.rs:360. Culprit land: ~DWRJEZV.
