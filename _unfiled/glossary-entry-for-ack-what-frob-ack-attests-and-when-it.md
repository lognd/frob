+++
id = "01M7CAYH7CTBT2SXY4DHJ4VN61"
title = "Glossary entry for ack (what frob ack attests and when it goes stale)"
type = "docs"
category = "todo"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-11-14T06:12:07Z"
updated = "2026-11-14T06:51:48Z"
idempotency_key = "gf-docs/glossary/ack.md"
labels = ["good-first"]
scope = ["docs/glossary/ack.md", "docs/README.md"]

[[acceptance]]
text = "Given docs/glossary/ack.md, when read, then it has the header block, explains what frob ack attests and when it goes stale, and is indexed in docs/README.md"
bound = false
+++

## Start here
Read docs/glossary/ (an existing entry for the page shape), docs/README.md (generated: run gob-dev gen all after adding the page) and the docs header-block rule DOC003 (Status, Owner, Decisions, Audience lines after the H1). Write docs/glossary/ack.md explaining what frob ack attests and when it goes stale. Test: frob check --ticket passes. Ask the coordinator if unsure.
