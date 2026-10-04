+++
id = "01M3AXSD9HXZXAR6CW4MATNJYX"
title = "STORE301: many-to-many relationship modeled in a document store with manual application-side join loops"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSDBCZ0WN62JE8P0BQRA2"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:02Z"
aliases = ["T-6449"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_strata_mismatch.py", "tests/fixtures/store/store301-document-manual-join-loop/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9RZ5GY6YQ2MDV558BD"
+++

Rule id: STORE301 (research file section 8, cross-cutting signal #1).

Authority: MongoDB's own reference-modeling docs document the join cost
of the reference approach as the explicit tradeoff against embedding --
https://www.mongodb.com/docs/manual/tutorial/model-referenced-one-to-many-relationships-between-documents/.

Code shape: `find`/`find_one` call inside a loop over a previous query's
result set (the same N+1 shape STORE105 already flags) -- STORE301
differs from STORE105 by requiring the strata-declared paradigm for the
bound `code=` path be `document` (via T-STORE-302-ENGINE's vocabulary),
i.e. this fires only when the design ITSELF says "this is a document
store" and the code still walks it like a relational many-to-many join,
making it a declared-vs-observed mismatch rather than a bare call-shape
finding.

Detection: reuse STORE105's own N+1 detector, gate its output through
strata's declared `engine` paradigm for the bound node -- only surfaces
as STORE301 (not STORE105, which already fired independently) when the
binding's declared paradigm is `document`.

Positive-control fixture:
`tests/fixtures/store/store301-document-manual-join-loop/` (a `.strata`
fixture declaring `engine mongodb` bound to a Python file with the N+1
shape).

Relevance gate: strata `store` node declared with `engine` resolving to
`document` paradigm, AND pymongo/motor/mongoose import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
