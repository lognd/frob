+++
id = "01M3ZAYESJBF9E7PKC75NFTK3H"
title = "rules consume FileInfo: opaque F0 and partial-parse files are Unresolved or NotApplicable"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-02T22:14:51Z"
updated = "2026-10-02T23:40:06Z"
scope = ["crates/frob-obligations/**", "crates/frob-check/**", "crates/frob-tests/**", "crates/gob-check/**", "crates/frob-ack/**", "docs/reference/**", "Cargo.lock"]
+++

found while working ~5033RN1: gob-symbols now exposes SymbolGraph::file_info (fidelity, parse_status, is_opaque) and ReachSet poison, but no rule reads them yet; acceptance 2 of ~5033RN1 (every rule reports an adapter-less file Unresolved or NotApplicable) needs the rule crates to consume it. Also frob-tests touched_set stays Rust-only (G18).
