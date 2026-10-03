+++
id = "01M404FZ1G52F6QMYYGS3AFCP4"
title = "grimble SYS003, SYS008-011 examine no subject on this repository: framework warning on every run"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:41:20Z"
updated = "2026-10-03T05:54:43Z"
idempotency_key = "m2-sys-zero-subjects"
labels = ["milestone:2"]
scope = ["crates/grimble-check/**", "crates/grimble-bind/**"]

[[acceptance]]
text = "Given this repository, when frob check runs, then no grimble rule reports zero subjects; each either examines subjects or reports NotApplicable with a reason"
bound = false
+++

Every frob check prints 'grimble rule SYSnnn examined no subject and reported nothing (a framework bug, not clean evidence)' for SYS003, SYS008, SYS009, SYS010, SYS011. Either the rules are wired to subjects they never receive (a real bug: a rule that should apply is silently inert), or this repository's three-node model genuinely has nothing for them (then they must declare NotApplicable with a reason instead of zero subjects). Determine which per rule, fix the wiring or declare applicability, and add a test per rule with a model that gives it subjects.
