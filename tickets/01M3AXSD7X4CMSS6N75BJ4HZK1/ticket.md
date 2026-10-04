+++
id = "01M3AXSD7X4CMSS6N75BJ4HZK1"
title = "STORE105: `find`/`find_one` inside a loop over a prior query's result (N+1, MongoDB)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:57:59Z"
aliases = ["T-6397"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_mongo.py", "tests/fixtures/store/store105-mongo-n-plus-1/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE105.

Authority: MongoDB Manual, "Model One-to-Many Relationships with
Document References": "If the number of books per publisher is
unbounded, this data model creates mutable, growing arrays" --
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/
(general reference-modeling join-cost framing this row's own authority
note in the research file draws the N+1 tradeoff from).

Call shapes:
- Python (pymongo/motor): `for parent in collection.find(...): child =
  other_collection.find_one({"parent_id": parent["_id"]})` (a DB call
  inside a loop over a prior query's result set)
- TS/JS: `for (const p of parents) { const c = await
  Other.findOne({parentId: p._id}) }`, mongoose `.populate()` in a loop

Detection: this is the SAME shape SQL101 already detects for a different
receiver kind -- import `frob.sql._orm_rules._for_loop_targets` and
`_attribute_accesses_on`/loop-body-call-scan helpers rather than
reimplementing the loop-body walk; swap SQL101's ORM-eager-load-name
check for a "no batched `$lookup`/aggregation call in the same function"
check.

Positive-control fixture:
`tests/fixtures/store/store105-mongo-n-plus-1/`.

Relevance gate: pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
