+++
id = "01M4D6NW55VM12ZT8D5HBYYRC6"
title = "Adapter hypothesis check: May sets must contain the true referent; adapters that cannot guarantee it emit Unknown (oracle corpus test)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T07:29:38Z"
updated = "2026-10-16T02:37:10Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given oracle corpora with known referents, when adapters resolve them, then every true referent is inside the emitted May set or the site is Unknown"
bound = true
+++

Decision (coordinator, from the formal review's R_lo <= R_true <= R_hi): a referent outside a May set is an adapter bug, not an evaluator case. Follow-up from ~JVT37ES.
