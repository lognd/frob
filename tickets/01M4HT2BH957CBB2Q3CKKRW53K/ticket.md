+++
id = "01M4HT2BH957CBB2Q3CKKRW53K"
title = "Land gate: a cancelled base CI check is Pending, not Red"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 1
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-10T02:25:28Z"
updated = "2026-10-17T07:48:35Z"
scope = ["crates/frob-release/src/ci.rs"]

[[acceptance]]
text = "Given a base tip whose only non-passing check run concluded cancelled, when the land gate judges it, then the state is Pending, never Red or Green"
bound = true
+++

found while working ~BN7DCP3: CI now cancels superseded runs, and classify/Check::from treat conclusion cancelled as a failure, so a land that fetched an older base tip right as a newer push cancelled its run reads Red. Treat cancelled (superseded) as Pending with a warning.
