+++
id = "01M7CAYH4DH7619Y42EX0QMDF0"
title = "Glossary entry for obligation (what the obligation graph is and where its rules live)"
type = "docs"
category = "todo"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-11-14T06:12:07Z"
updated = "2026-11-14T06:51:47Z"
idempotency_key = "gf-docs/glossary/obligation.md"
labels = ["good-first"]
scope = ["docs/glossary/obligation.md", "docs/README.md"]

[[acceptance]]
text = "Given docs/glossary/obligation.md, when read, then it has the header block, explains what the obligation graph is and where its rules live, and is indexed in docs/README.md"
bound = false
+++

## Start here
Read docs/glossary/ (an existing entry for the page shape), docs/README.md (generated: run gob-dev gen all after adding the page) and the docs header-block rule DOC003 (Status, Owner, Decisions, Audience lines after the H1). Write docs/glossary/obligation.md explaining what the obligation graph is and where its rules live. Test: frob check --ticket passes. Ask the coordinator if unsure.
