+++
id = "01M4RN89XGXSXMSF2HV2FPSG41"
title = "crunk binary installs the gob-git content backend at startup (follow-up of NF2ZMQG)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-12T18:16:01Z"
updated = "2026-10-12T20:54:08Z"
scope = ["crates/crunk/Cargo.toml", "crates/crunk/src/main.rs"]

[[acceptance]]
text = "crunk binary calls gob_git::install_content_backend() before gob_product::main and depends on gob-git; crunk nextest suite passes"
bound = true
+++

found while working ~NF2ZMQG: gob-walk now takes its git content backend by injection; frob, grimble and gob-dev call gob_git::install_content_backend() first in main, crunk must too (add gob-git dependency) or its digests lose git normalization.
