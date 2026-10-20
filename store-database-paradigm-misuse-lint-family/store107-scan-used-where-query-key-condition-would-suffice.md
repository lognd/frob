+++
id = "01M3AXSD8V4QRHX1H7T1YB26XK"
title = "STORE107: `Scan` used where `Query` (key condition) would suffice, in a request handler (DynamoDB)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6427"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_dynamodb.py", "tests/fixtures/store/store107-dynamodb-scan-vs-query/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE107.

Authority: AWS docs, "Best Practices for Using Scan Operations" --
research-file fetch this pass returned only nav-shell content (likely
JS-rendered); AWS docs "Query and Scan Operations in DynamoDB" also
returned minimal content. Flagged **gap, JS-rendered** in the research
file. Blocked by T-STORE-401-GAPS pending either a successful re-fetch
with a real quote, or an alternate primary source.

Call shapes:
- Python (boto3): `table.scan(...)` inside a request handler/API view
  function
- TS/JS: `docClient.send(new ScanCommand({...}))` inside a request
  handler

Detection: call-shape match on `scan(`/`ScanCommand` plus call-site
reachability from a request-handler entry point (same reachability
helper as STORE106).

Positive-control fixture:
`tests/fixtures/store/store107-dynamodb-scan-vs-query/`.

Relevance gate: boto3 DynamoDB client detected AND a web framework
detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
