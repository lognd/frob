+++
id = "01M1T07NVGEMSZHP634ZBSN566"
title = "ASSERT001: no bare assert in src/**"
type = "security"
category = "todo"
priority = "low"
parent = "01M1QDTYV6Z35XFTPNT4QW70Y2"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3952"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/**"]

[[acceptance]]
text = "given a bare assert statement in a src/** module outside tests/, when frob check runs, then ASSERT001 fires naming the file and line"
bound = false

[[acceptance]]
text = "given the existing corpus, when the rule is first turned on, then a baseline/ratchet is used rather than a repo-wide failure"
bound = false
+++

F-179 (T-3942 item 5). The cheapest rule in either report per the consumer. Proposed in their first audit (T-3919, never decomposed/built) and the identical bare-assert pattern reappeared verbatim in the newest module they wrote for the delta audit. FINDING THIS WOULD HAVE CAUGHT: F-179 -- a bare assert statement in src/** used for a runtime/security-relevant check that a production build with -O strips silently. Rule: a lexical/AST gate rejecting bare assert in src/** (test files exempt), pointing the author at typani Result/ensure idioms instead. No prior ticket found via git grep for ASSERT001.
