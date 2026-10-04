+++
id = "01M43KP0RXKB1DJA8KGJTV288R"
title = "DSL001 fires on 95 frob:waive directives quoted in imported ticket.md bodies (markdown HTML-comment scan reads them as directives)"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-04T14:04:30Z"
updated = "2026-10-04T14:32:06Z"
scope = ["crates/gob-walk/**", "crates/gob-directives/tests/scan.rs", "crates/frob-check/tests/ledger_inert.rs", "crates/frob-ack/src/inputs.rs", "crates/frob-obligations/src/collect.rs", "crates/grimble-bind/src/frob_owned.rs", "crates/grimble-check/src/config.rs", "docs/design/README.md", "docs/design/code-model.md", "Cargo.lock"]
+++

found while working ~41MBK6Q: frob check on experimental reports error DSL001 unknown directive frob:waive at tickets/*/ticket.md (for example the first lines of tickets/01M1QDTYQEEAFC68ACF76TH9AC/ticket.md), 95 errors; the v1 import quoted v1 waive comments. Either register waive or make imported text inert.
