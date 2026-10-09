+++
id = "01M4FGXVQTN5NJ0JBGWAMVHK82"
title = "Repo packs load: packs/NAME.toml with [packs] enabled supplies atoms and the pack entity resolves"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:14Z"
updated = "2026-10-09T19:46:59Z"
idempotency_key = "logand-gaps-A2"
labels = ["adoption:logand-app", "grimble"]
scope = ["changelog.d/**", "crates/grimble-check/src/lib.rs", "crates/grimble-check/src/config.rs", "crates/grimble-check/src/packs.rs", "crates/grimble-check/tests/packs.rs", "crates/grimble-model/src/model.rs", "crates/grimble-model/src/atoms.rs", "crates/grimble/src/doctor.rs", "crates/grimble-model/src/rules.rs", "crates/grimble-check/src/sibling.rs"]

[[links]]
kind = "relates"
target = "01M3ZX7K7BN0CEADJFMCTGEA64"

[[acceptance]]
text = "Given packs/logand-effects.toml declaring fetch_url and [packs] enabled naming it, when grimble check runs, then may fetch_url is not MDL016 and the registry shows provenance repo:packs/logand-effects"
bound = false

[[acceptance]]
text = "Given a pack entity naming that pack, when grimble check runs, then no MDL004 and the not-loaded warning is gone"
bound = false

[[acceptance]]
text = "Given an enabled pack file that does not exist, when grimble check runs, then MDL004 names the missing path"
bound = false
+++

Repro 03-packs-not-loaded (~/projects/frob-v2-repros/logand-grimble-20261009/03-packs-not-loaded) and 01 (fetch_url client_storage html_render ffi eval sql need a repo pack). Today the check warns 'this build does not load packs yet', MDL004 on the pack entity, MDL016 on pack atoms. Minimal tier-1 slice (atoms only) of ~CTGEA64; the full loader, lock and tiers stay there.
