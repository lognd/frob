+++
id = "01M43AYJ2RMDD8DGZ5Q060142M"
title = "Pack scaffold: grimble-sysdesign (STORE, SYSDESIGN, GRAMMAR)"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:31:53Z"
updated = "2026-10-04T11:31:53Z"
idempotency_key = "crunk-plan-g_sd"
labels = ["area:grimble"]
scope = ["packs/grimble-sysdesign/**", "docs/grimble/packs/grimble-sysdesign.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[links]]
kind = "blocked-by"
target = "01M3ZX7K7BN0CEADJFMCTGEA64"

[[acceptance]]
text = "Given the scaffold, when `grimble rule catalog` runs, then STORE, SYSDESIGN and GRAMMAR show with one rule each"
bound = false

[[acceptance]]
text = "Given the pack lock, when verified, then the digest matches"
bound = false

[[acceptance]]
text = "Given a rule without examples, when the pack compiles, then it fails"
bound = false
+++

Pack directory, manifest, lock entry, one worked rule per family with examples, std-pack registration. These families lint stores, data and infrastructure design against the model; decide at pickup which rules read .grmb entities (grimble-model) and which read code (record in the manifest).
