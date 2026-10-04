+++
id = "01M3AXSD98B7YWA3X9VS85YXVC"
title = "STORE208: collection query missing index coverage (`find({})`/leading-wildcard `$regex`, MongoDB)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:52Z"
aliases = ["T-6440"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_mongo.py", "tests/fixtures/store/store208-mongo-scan-no-index/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE208.

Authority: MongoDB Manual, "Indexes": "Without indexes, MongoDB must
scan every document in a collection to return query results. If an
appropriate index exists for a query, MongoDB uses the index to limit
the number of documents it must scan" --
https://www.mongodb.com/docs/manual/indexes/.

Call shapes: pymongo `collection.find({})` with no filter/limit on a
collection referenced elsewhere as large; `collection.find({"field":
{"$regex": f"^.*{q}"}})`; TS/JS: `Model.find({})`,
`collection.find({field: {$regex: q}})` with leading wildcard.

Repo fact needed: index list from schema/migration files to confirm
absence of a matching index (the call shape itself is static: yes per
the research row, this repo fact just confirms it is not already
covered).

Positive-control fixture:
`tests/fixtures/store/store208-mongo-scan-no-index/`.

Relevance gate: pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
