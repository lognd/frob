+++
id = "01M1WJMD3K9F3KHS52FMZX27BF"
title = "exported check*/*Check symbol with no reference from a declared entrypoint list is a finding; PUBLIC_ALLOWLIST-shaped invariants are its concrete instance"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4211"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates"]
+++

Consumer F-317/H-1 (T-4135 sub-epic, shell round-3). frob check has no notion of 'this module exports a check*/*Check gate that no entry point calls'. A rule flagging an exported check*/*Check symbol in a scripts dir with no reference from a package manifest's script list would have caught both halves of the finding; the allowlist-desync half is a concrete instance of frob:invariant PUBLIC_ALLOWLIST == git ls-files <dir>, which the code already states in prose. Fixture-testable: partially -- the entrypoint-reference check is generic and testable against frob's own scripts/CLI; the specific allowlist-invariant shape is consumer-only.
