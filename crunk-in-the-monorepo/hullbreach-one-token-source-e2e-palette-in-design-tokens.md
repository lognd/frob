+++
id = "01M5XCVZK2S3FYG8KPS7YXEHNJ"
title = "Hullbreach one-token-source e2e: palette in design/tokens drives Tailwind, CSS, USS and C# and the ThrustRed drift fires"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T00:41:22Z"
updated = "2026-10-27T02:41:53Z"
labels = ["area:crunk"]
scope = ["crates/crunk/tests/e2e_tokens_hullbreach.rs, crates/crunk/tests/fixtures/hullbreach_tokens/**", "crates/crunk/tests/e2e_tokens_hullbreach.rs", "crates/crunk/tests/fixtures/hullbreach_tokens/**"]

[[links]]
kind = "blocked-by"
target = "01M5XCVMQBQWARH7HT8RYHA0KY"

[[acceptance]]
text = "Given a fixture with the hullbreach palette under design/tokens and a stress-fail literal differing from ThrustRed, when crunk tokens --check runs, then Tailwind, CSS, USS and C# outputs exist and the drift finding names ThrustRed and exits 1; given the literal reconciled, then it exits 0"
bound = true
+++

Epic exit criterion for phase 2. Test-only ticket over the existing exporters; use the crunk-tokens parity and drift code, do not add new product code.
