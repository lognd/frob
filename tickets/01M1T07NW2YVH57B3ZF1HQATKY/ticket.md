+++
id = "01M1T07NW2YVH57B3ZF1HQATKY"
title = "PROTO001: protocol conformance at wiring sites"
type = "security"
category = "triage"
priority = "high"
parent = "01M1QDTYTFZHQYMDHNFBSGQXJJ"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:00Z"
aliases = ["T-3970"]
labels = ["milestone:0.539.0", "v1-cluster:B4"]
scope = ["src/frob/arch/_protocol_excuse.py"]

[[acceptance]]
text = "given the code, when this ticket's first step runs, then it reports whether PROTO001 (as a rule id) is already registered anywhere and for what check, before any new detection logic is written"
bound = false

[[acceptance]]
text = "given a Protocol with no traceable non-test implementation bound at a named wiring site, when frob check runs, then the new rule fires"
bound = false
+++

T-3919 item 2. VERIFIED: git grep shows src/frob/arch/_protocol_excuse.py, src/frob/gates/_protocol_summary.py and PROTO001 already exist as strings in src/frob/gates/__init__.py/_waive.py -- but reading _protocol_excuse.py, that machinery is about EXCUSING a class from an abstraction-boundary check when it plausibly stands in for a Protocol, not about verifying a Protocol has a real non-test implementation bound at a named wiring site. So this is a DIFFERENT check under a name that may already be registered as a rule id -- confirm which PROTO001 (if any) is already live before building, since a rule id collision would be worse than a missing rule.

FINDING THIS WOULD HAVE CAUGHT: two Protocols sharing a name plus a setattr on app.state standing in for a real binding -- and generalizes to the in-memory-repos-in-production issue elsewhere in the same audit. Proposed rule: every consumer-side Protocol has a non-test implementation bound at a named wiring site (an explicit registration call, DI container binding, or app.state assignment with a traceable concrete type) -- not merely "a class of the same name exists somewhere."
