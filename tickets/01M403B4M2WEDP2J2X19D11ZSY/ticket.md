+++
id = "01M403B4M2WEDP2J2X19D11ZSY"
title = "Doc consistency: fold the docgen survey (existing include syntaxes, ratchet baseline, duplicate classes, keep-in-sync comments)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:21:13Z"
updated = "2026-10-03T05:24:05Z"
idempotency_key = "m2-doc-consistency-survey"
labels = ["milestone:2"]
scope = ["docs/design/**", "notes/research/docgen-survey.md"]

[[acceptance]]
text = "Given doc-consistency.md, when read, then each survey recommendation in docgen-survey.md section 5 is adopted or rejected with a reason"
bound = false
+++

notes/research/docgen-survey.md (1254 repositories): read existing include directives (mdBook, MkDocs snippets, Sphinx, AsciiDoc, MDX) as pointers instead of forcing a new syntax; named regions only, defined exactly once; a changed code region flags the prose around its includes; a shrink-only ratchet baseline for fact references (cpython nit-picky); harvest facts from generator inputs; duplicate detection thresholds and classes (versioned and translation docs exempt, agent-instruction mirrors, diverged near-copies ranked lower); keep-in-sync comments become pair suggestions; no spell, link or prose lint implementations, glue only.
