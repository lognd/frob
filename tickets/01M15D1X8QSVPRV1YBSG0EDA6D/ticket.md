+++
id = "01M15D1X8QSVPRV1YBSG0EDA6D"
title = "Fix frob:tests Class::method separator in check_runner.py (2 DRIFT002 findings)"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-08-29T00:00:00Z"
updated = "2026-08-29T00:00:00Z"
aliases = ["T-3351"]
labels = ["milestone:1.0.0", "v1-cluster:C4a"]
scope = ["src/frob/app/check_runner.py"]
+++

Deferred from T-3344 (gate:DRIFT burn-down) because T-3326 holds an in-progress lease on this file and landing would create CrossTicketLeakage. Same fix as T-3344's other 12 files: two frob:tests directives at lines ~351/354 use TestTaskProgressCallback::test_... (double-colon) instead of the graph's TestTaskProgressCallback.test_... (dot) qualname convention, so DRIFT002 flags them as unresolvable. Apply once T-3326 closes.
