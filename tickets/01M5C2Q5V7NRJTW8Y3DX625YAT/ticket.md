+++
id = "01M5C2Q5V7NRJTW8Y3DX625YAT"
title = "frob check accepts --trust-from REF and the CI check step passes it"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T07:16:54Z"
updated = "2026-10-20T08:17:31Z"
scope = ["crates/frob/src/**", "crates/gob-check/src/**", "crates/gob-dev/src/ci.rs", "crates/frob-check/src/options.rs", "crates/frob-check/src/verb.rs"]

[[acceptance]]
text = "Given frob check --trust-from REF, when a pack is absent from the lock at REF, then it reports Unresolved untrusted-in-change"
bound = false

[[acceptance]]
text = "Given the CI check step, when it builds its command, then it contains --trust-from and no other trust flag"
bound = false
+++

Found while working ~PPG901F. security.md 2.3 says check --trust-from REF is the only CI trust flag, but gob_check::trust_from is not wired to any CLI flag (frob check --help has no --trust-from) and the CI check step (crates/gob-dev/src/ci.rs, 'check --skip-tools') passes none. Wire the flag through frob check and make the CI check step pass --trust-from origin/experimental; ~PPG901F then switches nothing further but verifies ci.yml.
