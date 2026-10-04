+++
id = "01M1T07NW78MGWRF7HZQMPSRAV"
title = "evidence satisfaction must exclude xfail/xpass/skip by default"
type = "security"
category = "triage"
priority = "medium"
parent = "01M1QDTYTRW714S858S0TP6YWM"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:05:02Z"
aliases = ["T-3975"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/testing/_models.py"]

[[acceptance]]
text = "given the current outcome-handling code, when this ticket's first step runs, then it reports whether xfail/xpass/skip currently satisfy evidence in this repo before any code change"
bound = false

[[acceptance]]
text = "given the fix, when a test outcome is xfail/xpass/skipped and no explicit opt-in is declared, then it does not satisfy frob:tests or ticket evidence"
bound = false

[[acceptance]]
text = "given an explicit opt-in is declared, when such an outcome occurs, then it is reported as a distinct countable state, not folded into passed"
bound = false
+++

T-3928 edge/ops-unique item. THIS ONE BEARS ON FROB'S OWN EVIDENCE INTEGRITY, per the epic's own framing -- if xfail/xpass/skip satisfies frob:tests or ticket evidence today, every fail-then-pass claim this repo's own gates rely on is weaker than it reads.

FINDING THIS WOULD HAVE CAUGHT: a process gate that pytest-xfails away every violation and can never fail, and a component whose whole suite skips when a toolchain is absent -- both counted as passing evidence in the consumer's frob:tests/ticket-evidence bindings.

VERIFY FIRST (before building): read src/frob/testing/_models.py and _runners.py's outcome handling -- does the current evidence-satisfaction check accept outcome states other than "passed" today (xfail, xpass, skipped)? This is a claim about our own code and must be measured, not assumed, before deciding whether this is a real gap here too or only in the consumer's own pytest config.

Proposed default: evidence satisfaction requires outcome==passed; an explicit opt-in for xfail/skip-as-evidence must exist as a distinct, COUNTABLE state (reported separately, not folded into "green") rather than silently accepted as equivalent to passed.
