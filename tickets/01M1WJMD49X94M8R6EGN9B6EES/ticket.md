+++
id = "01M1WJMD49X94M8R6EGN9B6EES"
title = "frob:invariant: flag a component whose only bound tests exercise one happy-path fixture value for a parameter-shaped input"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4233"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_inv.py"]
+++

Consumer F-325/H2-2 first half: a credential-parsing invariant had no evidence to bind to because the only bound test used a password with no reserved characters -- 'no bound test varies input X' is checkable from the test source for parameter-shaped inputs. Adjacent to T-3997 (TESTMOCK001: fully-mocked subjects need a non-mocked companion) -- same family (a test that LOOKS like coverage but structurally cannot exercise the failure mode) but a distinct trigger (single-fixture-value vs full-mock). Fixture-testable: YES, generically, with a synthetic parameterized function in frob's own tree.
