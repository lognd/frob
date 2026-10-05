+++
id = "01M416233QBRZYW9001M3JKSGA"
version = "0.532.0"
goal = "someone outside this repository can install frob and run its whole loop"
state = "open"
epics = ["01M4065Y4N6DQG30TRSP2QNP8T"]
created = "2026-10-03T15:27:57Z"
updated = "2026-10-05T05:50:35Z"

[[criteria]]
text = "binaries and wheel install on the five targets with artifact smoke"
bound = true

[[criteria]]
text = "CHANGELOG compiled from fragments"
bound = true

[[criteria]]
text = "Owner decision 2026-10-05 (relaxed from two full cycles): cloc and mdcat are managed by frob v2, and at cut time ticket doctor is clean in both with no event count lower than at the previous check; the Unity and Python trial on project-hullbreach follows the release"
bound = true
+++
