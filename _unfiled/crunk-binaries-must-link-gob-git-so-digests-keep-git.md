+++
id = "01M55VA1V2RX832AYQ5AG4YATH"
title = "crunk binaries must link gob-git so digests keep git normalization (gob-walk uses a link-time provider)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T21:11:57Z"
updated = "2026-10-17T22:47:00Z"
scope = ["crates/crunk/**", "docs/design/git-io.md"]

[[acceptance]]
text = "Given the crunk lib/binary link set, when providers are enumerated, then a gob_walk::SourceProvider (gob-git) is registered"
bound = true
+++

found while working ~NF2ZMQG: ContentSource::locate resolves gob-git via inventory; crunk bins do not link gob-git so they fall back to raw reads.
