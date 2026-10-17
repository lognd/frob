+++
id = "01M55VA1V2RX832AYQ5AG4YATH"
title = "crunk binaries must link gob-git so digests keep git normalization (gob-walk uses a link-time provider)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T21:11:57Z"
updated = "2026-10-17T21:11:57Z"
scope = ["crates/crunk/**"]
+++

found while working ~NF2ZMQG: ContentSource::locate resolves gob-git via inventory; crunk bins do not link gob-git so they fall back to raw reads.
