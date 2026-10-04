+++
id = "01M43AVKMT52QCG7DGNQ4J906S"
title = "Parity harness: Rust crunk against the Python corpus with a reasoned divergence list"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:16Z"
updated = "2026-10-04T11:30:16Z"
idempotency_key = "crunk-plan-parity"
labels = ["area:crunk"]
scope = ["crates/crunk/tests/parity.rs", "crates/crunk/tests/parity/**", "tests/crunk-parity/divergences.toml"]

[[links]]
kind = "blocked-by"
target = "01M43ARW68Z46ETMAQ6CB4N03R"

[[links]]
kind = "blocked-by"
target = "01M43ARZH9F9MCPJCKXM635E0X"

[[links]]
kind = "blocked-by"
target = "01M43ATCF5GGK59S96K1ZF0G9C"

[[links]]
kind = "blocked-by"
target = "01M43ATCQVX9A1TJ6A4AE48FDX"

[[links]]
kind = "blocked-by"
target = "01M43ATCZXK3B3952GGEBT1ASJ"

[[links]]
kind = "blocked-by"
target = "01M43ATD7ZGTNCY5036AYEJR7P"

[[acceptance]]
text = "Given the corpus, when the harness runs, then every project passes or has a reasoned divergence"
bound = false

[[acceptance]]
text = "Given a divergence entry that no longer differs, when the harness runs, then it fails and names the entry"
bound = false

[[acceptance]]
text = "Given the harness, when run in CI, then it is a required job for crates/crunk-* changes"
bound = false
+++

Run the Rust crunk over every corpus project and diff against the Python expected files; every difference is either fixed or recorded in divergences.toml with a reason (for example the added did-you-mean, the gob.sibling/1 envelope, improved Unresolved states). The harness fails on an unlisted difference and on a listed one that no longer differs. This is the gate for retiring the Python crunk (docs/design/monorepo.md 5 step 3).
