+++
id = "01M4527J4M910ZZBJZXMDZJQZQ"
title = "cargo dev ci check step needs the workspace's own sibling binaries built, not whatever is on PATH"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "lognd"
created = "2026-10-05T03:37:59Z"
updated = "2026-10-06T05:30:40Z"
scope = ["crates/gob-dev/src/ci.rs", "changelog.d/01M4527J4M910ZZBJZXMDZJQZQ.*"]

[[acceptance]]
text = "Given a machine with no grimble or crunk installed, when cargo dev ci --step check runs, then it builds and uses the workspace siblings and reports no SIB001"
bound = true
+++

cargo dev ci's check step runs frob check, which needs the sibling grimble (and soon crunk) binary; on a fresh machine or goway helper it is absent ("program not found: grimble"), so check fails with a required SIB001 Unresolved that has nothing to do with the change under test (seen on ~N2HND27's remote run 2026-10-05, and locally earlier). Make the step self-sufficient: declare in gob-dev's ci.rs that check depends on building the sibling binaries of this workspace (frob-cli, grimble, crunk) and run frob check with those freshly built siblings discovered next to the frob executable (D87 sibling discovery), never whatever is on PATH. Together with ~NHAXXXJ (ledger ref absent on --with-git clones) this makes the whole cargo dev ci pass remotely.
