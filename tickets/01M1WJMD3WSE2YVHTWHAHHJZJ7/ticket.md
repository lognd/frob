+++
id = "01M1WJMD3WSE2YVHTWHAHHJZJ7"
title = "purity/ownership invariant: a controller documented Pure must not be wired to a caller that writes its output back into the buffers it read"
type = "task"
category = "triage"
priority = "low"
parent = "01M1WJMD1X14Z9P76XPX0QQ0NM"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:06:02Z"
aliases = ["T-4220"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_inv.py"]
+++

Consumer F-357/H4-8 (T-4157): a controller documented 'Pure: reads world, never mutates it' is wired to a caller that applies its outputs to the same buffers it read, mutating real state despite the documented contract. A general purity/ownership rule is beyond current gates; the practical version is a frob:invariant on the caller's state at a defined checkpoint, bound to a test. Fixture-testable: mechanism is generic and partially testable with a synthetic pure-function fixture in frob's own tree; the consumer's specific attract-mode domain does not exist here.
