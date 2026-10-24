+++
id = "01M5NYTXARKJTMT6G33G2WTCQG"
title = "gob-ir taint trusts Observation::Reach under poison: a careless Pc check returning Reach{lo:false,hi:false} still yields Clean"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-24T03:21:26Z"
updated = "2026-10-24T03:22:27Z"
scope = ["crates/gob-ir/**"]

[[acceptance]]
text = "a Pc check returning a definite Reach under a poisoned subject never yields Clean; a test proves it"
bound = false
+++

Found by the ~T7M99CH implementer: taint in crates/gob-ir/src/eval/program.rs treats Observation::Reach as the check's own statement.
