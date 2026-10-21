+++
id = "01M43AWPD2DYMS2CVTJRD56D5R"
title = "Pack scaffold: grimble-websec (WEBSEC into SEC, SQL, COMPLY and PII, ROUTE, WEBPERF server)"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:30:51Z"
updated = "2026-10-21T10:57:35Z"
idempotency_key = "crunk-plan-g_sec"
labels = ["area:grimble"]
scope = ["packs/grimble-websec/**", "docs/grimble/packs/grimble-websec.md", "crates/grimble-check/src/websec_pack.rs", "crates/grimble-check/src/lib.rs", "crates/grimble-check/Cargo.toml", "Cargo.lock", "crates/grimble-check/tests/websec_pack.rs", "changelog.d/01M43AWPD2DYMS2CVTJRD56D5R.added.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[links]]
kind = "blocked-by"
target = "01M3ZX7K7BN0CEADJFMCTGEA64"

[[acceptance]]
text = "Given the scaffold, when `grimble rule catalog` runs, then WEBSEC, SQL, COMPLY, ROUTE and WEBPERF show with one rule each and WEBSEC ids sit under SEC"
bound = true

[[acceptance]]
text = "Given the pack lock, when verified, then the digest matches the pack tree and PACK001-008 are clean"
bound = true

[[acceptance]]
text = "Given a rule without examples, when the pack compiles, then it fails"
bound = true
+++

Create the pack directory and manifest (packs.md tier-1 data file: families, languages, vocabularies, atoms), pack lock entry, one worked GRL rule per family with firing and clean example, std-pack registration in grimble. WEBSEC registers its ids inside the SEC family namespace (rules.md section 3); because no SEC or PII family ticket exists, this ticket also adds the SEC and PII family rows to the registry (metadata only) and records whether they live in the pack or in grimble-lints (design gap). Capability atoms for db.query and net come from the core-effects pack, not redefined here.
