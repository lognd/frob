+++
id = "01M4HAJZA6JTNSSGJYV040TA9M"
title = "check --ticket and land run repo-wide PM rules (PM033 replenish took 99.8 s of a 173 s ticket check); skip diff-independent PM rules there and keep them in the full check and CI"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4GRTA9XBJCM2RY98HWZXYC7"
reporter = "lognd"
created = "2026-10-09T21:54:55Z"
updated = "2026-10-09T22:55:13Z"
scope = ["crates/frob-check/src/product.rs", "changelog.d/**", "crates/gob-check/src/product.rs", "crates/gob-check/src/repo.rs", "crates/gob-check/tests/pipeline.rs", "crates/gob-check/src/pipeline.rs"]

[[acceptance]]
text = "Given frob check --ticket or frob land, when the check runs, then PM rules that do not depend on the ticket's diff (PM033 replenish, cycle and backlog health) are not evaluated and the report lists them as not_evaluated with reason 'repo-wide, runs in full check'; a plain frob check still evaluates them"
bound = true

[[acceptance]]
text = "Given PM033 in a full check, when it computes the ready queue, then it uses the same fast doable path as ticket doable (~ZZQ6PA9), measured under 5 s on this repository"
bound = true
+++

Measured 2026-10-09 (check --ticket ~807V4XM, land binary, load 83): repo:replenish 99.8 s, sibling:grimble 57.1 s, repo:obligations 18.7 s, file-rules 13.0 s, all cargo stages about 11 s; total 173 s. Owner goal: lands under a minute.
