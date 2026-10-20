+++
id = "01M336K750ZSY30F2J2Y38ENDF"
title = "frob ticket points/tokens missing LEDGER_VERB_STRATEGY entry (T-5132 regression)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5280"]
scope = ["src/frob/app/ticket_runner/_ledger_mirror.py"]
+++

T-5132 landed frob ticket points/tokens verbs but never registered them in _ledger_mirror.LEDGER_VERB_STRATEGY (T-2603) -- _ledger_mirror.py was not in T-5132's declared scope. Every frob ticket points/tokens invocation currently crashes with 'has no LEDGER_VERB_STRATEGY entry'. Fix: add both verbs as GENERIC_COMMIT_MIRRORED, same as milestone/priority.
