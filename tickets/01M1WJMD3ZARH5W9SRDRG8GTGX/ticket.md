+++
id = "01M1WJMD3ZARH5W9SRDRG8GTGX"
title = "split a display-only error-code list into a display axis and a needs-client-recovery axis, and require the totality test to answer both"
type = "task"
category = "triage"
priority = "low"
parent = "01M1WJMD26NR9SKQCEFEHS7ENJ"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4223"]
labels = ["milestone:1.1.0", "v1-cluster:B4"]
scope = ["src/frob/gates"]
+++

Consumer F-362/M4-5 (T-4166): a display-layer list (IGNORED_ERROR_CODES) is used to discharge a recovery question -- the totality test checks only that every backend code appears in one of two lists, not whether the code needing a recovery ACTION (e.g. re-bootstrapping CSRF) got one. Split into DISPLAY_ONLY and a second, independently-answered axis, with the totality test asserting both. Related family to T-4166's own registry-vs-surface totality theme (F-373 in T-4175) but a distinct code path -- kept separate rather than merged. Not fixture-testable in frob's own tree: no client/server error-code registry duo exists here.
