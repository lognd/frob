+++
id = "01M4HBJC1D4S5Z5XNHZH33QRVD"
title = "Raise [check] sibling_timeout_secs from 120 to 600: the grimble sibling times out under agent load (SIB001 is required and fails the gate)"
type = "chore"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T22:12:04Z"
updated = "2026-10-09T22:12:26Z"
scope = ["frob.toml", "changelog.d/**"]

[[acceptance]]
text = "Given frob.toml, when the change lands, then [check] sibling_timeout_secs is 600 with a comment stating why"
bound = false
+++

2026-10-09: ~EK8T90W's check --ticket failed only on SIB001 (grimble timed out at 120 s, load 80+); sibling:grimble measured 57 s at load 83. ~77B0T1W (grimble bind cache) is the real fix.
