+++
id = "01KZ7KGKJ7TR8HEBH86Y18T290"
title = "Language expansion: remaining ranked languages, in research-recommended batches"
type = "task"
category = "triage"
priority = "low"
parent = "01KZ7KGKHXGS6W2YAVRY27W0D5"
reporter = "human"
created = "2026-08-05T00:00:00Z"
updated = "2026-10-04T21:08:42Z"
aliases = ["T-1607"]
labels = ["v1-cluster:D2", "triage:accepted"]
scope = ["tickets/T-1607/**"]
+++

Implement the remaining ranked languages from the research ticket's target list, in the batch order it recommends, after the five named languages have proven the contract.

Split into further child tickets per batch rather than attempting all at once -- this ticket is the placeholder the research output turns into a concrete plan. Each batch must clear the parameterized adapter conformance suite before the next begins.

Expect the cost per language to FALL sharply after the first few if the contract is right, and to stay flat if it is wrong. A flat cost curve is the signal that the contract ticket did not actually succeed and should be revisited before continuing -- report it rather than grinding through.

Cannot be meaningfully split yet: this ticket's own job is to turn
T-1598's research output (the ranked 20-50 language list, sourced
across TIOBE/RedMonk/Octoverse/SO/IEEE Spectrum, with the recommended
batch order) into concrete per-batch child tickets. T-1598 was
deliberately deferred -- it requires live multi-source web research and
must not be attempted from model memory (see T-1598's own body note).

Manufacturing a batch order or a language ranking here to unblock this
ticket would be the exact mistake T-1598's deferral was meant to
prevent, just one ticket downstream. Leaving this queued, untouched,
until T-1598 actually produces its research output. No child tickets
filed this round.
