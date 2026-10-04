+++
id = "01M43KP0RXKB1DJA8KGJTV288R"
title = "DSL001 fires on 95 frob:waive directives quoted in imported ticket.md bodies (markdown HTML-comment scan reads them as directives)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "lognd"
created = "2026-10-04T14:04:30Z"
updated = "2026-10-04T15:17:25Z"
scope = ["crates/gob-walk/**", "crates/gob-directives/tests/scan.rs", "crates/frob-check/tests/ledger_inert.rs", "crates/frob-ack/src/inputs.rs", "crates/frob-obligations/src/collect.rs", "crates/grimble-bind/src/frob_owned.rs", "crates/grimble-check/src/config.rs", "docs/design/README.md", "docs/design/code-model.md", "Cargo.lock", "crates/frob-check/src/snapshot.rs", "crates/frob-check/src/filecheck.rs", "crates/gob-directives/src/comments.rs", "docs/design/tickets.md"]

[[acceptance]]
text = "Markdown scanning reads only HTML comments outside code and front matter: prose and front matter mentioning frob:waive yield no directive, an HTML comment still does"
bound = true

[[acceptance]]
text = "Text under the ledger directory is never a live directive: one FileRole classification makes directive scans and the per-file obligation rules skip ledger files"
bound = true
+++

found while working ~41MBK6Q: frob check on experimental reports error DSL001 unknown directive frob:waive at tickets/*/ticket.md (for example the first lines of tickets/01M1QDTYQEEAFC68ACF76TH9AC/ticket.md), 95 errors; the v1 import quoted v1 waive comments. Either register waive or make imported text inert.
