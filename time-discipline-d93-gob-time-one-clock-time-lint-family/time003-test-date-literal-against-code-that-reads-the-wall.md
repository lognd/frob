+++
id = "01M44R5WJRXFM7RP45R24CQJDM"
title = "TIME003: test date literal against code that reads the wall clock"
type = "story"
category = "todo"
priority = "low"
parent = "01M44R5D47XBH3E2N3B8FNMT9F"
reporter = "lognd"
created = "2026-10-05T00:42:19Z"
updated = "2026-10-05T00:42:32Z"

[[links]]
kind = "blocked-by"
target = "01M44R5W4WJEXFM000S8KVQQN5"

[[acceptance]]
text = "Given a test with a hardcoded future date reaching a today() read with no clock injected, when grimble checks it, then TIME003 fires"
bound = false

[[acceptance]]
text = "Given a test whose dates are relative to an injected clock, when grimble checks it, then TIME003 stays quiet"
bound = false
+++

rules.md 3.2 (D93): TIME003 test-date-vs-wall-clock: a test that builds or asserts a calendar date or timestamp literal while code it reaches (call graph) reads the wall clock with no clock injected, the exact shape of ~AAZFNR5. Advisory by default; Unresolved where reach is undecided, with a fidelity row. Must-fire fixture reproducing ~AAZFNR5 (hardcoded future date vs a today() read), must-stay-quiet fixtures for relative dates and for an injected fixed clock.
