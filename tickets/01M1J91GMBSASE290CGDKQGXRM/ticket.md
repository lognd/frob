+++
id = "01M1J91GMBSASE290CGDKQGXRM"
title = "frob coverage --full fails with no data to report, injects -n without xdist"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-03T00:00:00Z"
updated = "2026-09-03T00:00:00Z"
aliases = ["T-3723"]
labels = ["milestone:1.1.0", "v1-cluster:C4a"]
scope = ["src/frob/coverage/**"]
+++

apollo FROBLEMS.md 2026-09-03: frob coverage --full runs pytest with --cov-report= then coverage xml -i, which dies with 'No data to report' (no .coverage produced by its own pytest invocation). Also its first failure mode was injecting -n 12 into a repo without pytest-xdist installed (exit 4 usage error, reported as 'suite was RED'). Manual workaround: uv run pytest --cov + uv run coverage xml -i + frob check --stamp-coverage works.
