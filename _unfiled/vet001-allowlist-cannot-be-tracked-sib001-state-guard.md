+++
id = "01M73470XDYYF3D5BV77G165PS"
title = "VET001 allowlist cannot be tracked: SIB001 state guard refuses .grimble/vet.toml"
type = "bug"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-11-10T16:21:15Z"
updated = "2026-11-10T16:21:18Z"

[[acceptance]]
text = "Decide and implement: VET001 reads .grimble/vet.toml from the committed tree, but gob-trust check_state_untracked (SIB001/E-STATE-TRACKED) refuses any tracked .grimble/ file, so no bumped direct dependency can land. Either exempt only .grimble/vet.toml in guard.rs (security call: allowlist becomes PR-editable, reviewed in diff) or move the allowlist outside the state dir. Unblocks ~FBF3ZS0 (branch ticket/FBF3ZS0, rusqlite 0.41 clears RUSTSEC-2026-0459, evidence bound)."
bound = false
+++
