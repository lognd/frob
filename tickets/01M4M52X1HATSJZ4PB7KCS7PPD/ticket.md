+++
id = "01M4M52X1HATSJZ4PB7KCS7PPD"
title = "gob-walk ContentBackend trait implemented by gob-git, injected by the binaries; no gix under gob-walk, gob-ir, gob-symbols, grimble-model (audit M8 core)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:29Z"
updated = "2026-10-12T18:23:38Z"
scope = ["crates/gob-walk/**,crates/gob-git/**,crates/gob-ir/**,crates/gob-symbols/**,crates/gob-check/**,crates/frob-ack/**,crates/frob-tests/**,crates/frob/**,crates/grimble/**,crates/crunk/**,Cargo.lock,changelog.d/**"]
+++

Split from ~NF2ZMQG. gob-git -> gob-walk flips the edge, so trait and impl cannot land alone (cycle). Needs a process-wide backend hook in gob-walk (ContentSource::locate has 9 callers), installed by the frob, grimble and crunk mains, with a one-time warn when a git checkout is read with no backend (CRLF digests would silently differ). Acceptance: test over cargo metadata that no gix crate is in the closure of gob-walk, gob-ir, gob-symbols, grimble-model; CRLF normalization test still passes through the hook.
