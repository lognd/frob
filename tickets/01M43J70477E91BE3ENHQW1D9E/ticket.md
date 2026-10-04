+++
id = "01M43J70477E91BE3ENHQW1D9E"
title = "gob-git: concurrent CAS writers test is flaky under load (CasExhausted)"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-04T13:38:49Z"
updated = "2026-10-04T21:23:51Z"
scope = ["crates/gob-git/src/ledger.rs", "crates/gob-git/tests/ledger.rs", "docs/design/git-io.md"]

[[acceptance]]
text = "Given a heavily loaded host, when the concurrent CAS writers test runs 50 times, then it passes every time"
bound = true

[[acceptance]]
text = "Given the CAS retry policy, when it is documented, then the guarantee the test asserts matches the documented guarantee"
bound = false
+++

Observed 2026-10-04 on goway helper quasar under a wave of concurrent builds: gob-git test twenty_four_concurrent_writers_all_win_with_backoff failed with CasExhausted during cargo dev ci for ~M0388X5 (unrelated change). The test asserts every one of 24 concurrent writers eventually wins; under CPU contention the bounded retry budget runs out. Decide structurally: either the retry budget is time-based with jittered backoff sized so the property holds under load (and the test proves it with a deterministic scheduler or injected clock), or the property is weakened to what the product actually guarantees and the test asserts that. The test must not depend on wall-clock speed of the host.
