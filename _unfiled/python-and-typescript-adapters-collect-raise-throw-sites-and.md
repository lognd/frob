+++
id = "01M68WWDX3FNVTW9XRN2J7R2HK"
title = "Python and TypeScript adapters: collect raise/throw sites and callee errors into error_flow facts"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T11:52:53Z"
updated = "2026-10-31T12:31:47Z"
labels = ["no-story", "grimble"]
scope = ["crates/gob-symbols/src/python.rs", "crates/gob-symbols/src/typescript/**"]

[[acceptance]]
text = "Given a Python def raising PaymentDeclined and calling httpx, when folded, then ErrorCollector yields Bounds with the raise in lo and callee errors in hi; a TS throw yields Unknown with a reason"
bound = true
+++

Follow-up of ~589WNWE: adapter wiring not done.
