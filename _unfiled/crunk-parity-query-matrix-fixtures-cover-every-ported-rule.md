+++
id = "01M7EXTZ14EFV4P92807PW3SMA"
title = "crunk parity: query matrix fixtures cover every ported rule family"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
idempotency_key = "crunkplan-3049d181e678"
labels = ["no-story"]

[[acceptance]]
text = "each listed family has at least one expected violation compared with Python output"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding M3.
Evidence: only CONTRAST001 and TOKENS001 appear in the matrix
Remedy: extend fixtures so COLOR, SPACE, TYPE, RADIUS, SIZE, LAYER, ORG, TW, BP each fire once
Crates/files: tests/crunk-parity/expected/matrix, crates/crunk/tests/it/query_parity.rs
Verify against HEAD first; the audit ran on a stale binary.
