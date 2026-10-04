+++
id = "01M30M6G1WHSAE0B70RX1VYDH2"
title = "INV003: seven new gate/strata docs make 'only' claims with no frob:invariant marker"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-10-04T21:02:43Z"
aliases = ["T-5180"]
labels = ["milestone:0.534.0", "v1-cluster:B3d"]
scope = ["docs/modules/gate-inv011-forbidden-constant-reachability.md", "docs/modules/gate-race001.md", "docs/modules/gate-registration.md", "docs/modules/gate-sys111-ratchet-auto-accept.md", "docs/modules/gate-testmock001.md", "docs/modules/gate-time-stable-invariant.md", "docs/strata/dataset-construct.md"]
+++

MEASURED 2026-09-21 05:05 (frob check --base dev after the overnight drain): 7 INV003 errors. Each listed doc (all landed in the last two days: T-3962, T-3953, T-4661, T-3997 and siblings) makes an exclusivity/normative claim (regex \bonly\b) and carries no <!-- frob:invariant INV-### --> marker naming a real invariant. Fix per file: bind an existing invariant that covers the claim, add one in invariants/ if none does, or reword to drop the normative claim. Verify: INV003 count 7 -> 0.
