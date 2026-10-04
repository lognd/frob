+++
id = "01M3AXSDAWFSGDSJSME2SE123B"
title = "STORE207: single-table DynamoDB design with no documented access-pattern key schema"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:45Z"
aliases = ["T-6492"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_dynamodb.py", "tests/fixtures/store/store207-dynamodb-single-table-no-schema/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE207.

Authority: AWS docs, "Best Practices for Designing and Architecting with
DynamoDB" --
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general-nosql-design.html
(fetched; confirms the page covers this topic but did not yield a short
pull-quote distinct from the page title/nav this pass). Research file
flags this **partial gap**. Blocked by T-STORE-401-GAPS.

Call shapes: `table.put_item(Item={...})` with heterogeneous `Item`
shapes and a generic `PK`/`SK` naming convention but no access-pattern
doc/tests; TS/JS: `docClient.send(new PutCommand({...}))` same shape.

Repo fact needed: presence (or absence) of a repo-tracked access-pattern
doc (a `docs/`-tree file referencing the table's `PK`/`SK` design) --
this is the "documented" half of the check; heterogeneous `Item` shape
detection is the call-shape half.

Positive-control fixture:
`tests/fixtures/store/store207-dynamodb-single-table-no-schema/`.

Relevance gate: boto3 DynamoDB client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
