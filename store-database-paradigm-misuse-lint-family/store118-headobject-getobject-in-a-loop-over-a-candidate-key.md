+++
id = "01M3AXSD9AFR9Q42F9DAHKN41F"
title = "STORE118: `HeadObject`/`GetObject` in a loop over a candidate key list to filter by metadata (S3)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6442"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_object.py", "tests/fixtures/store/store118-s3-head-object-loop/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE118.

Authority: same listing-API page family as STORE117; S3 has no
query-by-metadata API, so any "query" necessarily becomes N
`HeadObject` calls -- structural absence of the capability is the
signal. Research file flags this row **gap** (no dedicated quote
sourced this pass). Blocked by T-STORE-401-GAPS.

Call shapes:
- Python: `for key in keys: s3.head_object(Bucket=b, Key=key)` to
  filter by metadata before use
- TS/JS: loop of `HeadObjectCommand` calls

Detection: S3 metadata call inside a loop over a candidate key list --
same N+1 family as STORE105/STORE116, reuse the shared loop-body
helpers.

Positive-control fixture:
`tests/fixtures/store/store118-s3-head-object-loop/`.

Relevance gate: boto3 (or equivalent) S3 client import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
