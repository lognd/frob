+++
id = "01M1WJMD3BRP73FG6PKCRB9NNR"
title = "test.runner rootdir resolution must not depend on which path subset pytest was invoked with"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:06:46Z"
aliases = ["T-4203"]
labels = ["milestone:1.1.0", "v1-cluster:C4a"]
scope = ["src/frob/testing"]
+++

Consumer F-338 (T-4135). A nested pyproject.toml's [tool.pytest.ini_options] wins when pytest is invoked with only its own subtree, and the root's pythonpath (needed to import a sibling scripts/ dir) is silently dropped -- so a system test passes standalone and fails from the repo root, or vice versa. The configured test.runner invocation must resolve the same rootdir regardless of which paths it is given. Fixture-testable: YES.
