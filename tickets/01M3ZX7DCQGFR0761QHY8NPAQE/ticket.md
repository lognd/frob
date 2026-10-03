+++
id = "01M3ZX7DCQGFR0761QHY8NPAQE"
title = "GRL parser: the twenty constructs to an AST"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:19Z"
updated = "2026-10-03T10:18:18Z"
idempotency_key = "m2-grl-parse"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/grl/ast.rs", "crates/gob-plan/src/grl/parse/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX779NSRZ97ZQM5DP3BZJZ"

[[acceptance]]
text = "Given each of the ten rules of grl-spec section 12, when parsed, then an AST is produced with spans for every clause, header, example and explain block"
bound = true

[[acceptance]]
text = 'Given `lang "*"`, when parsed, then it is accepted with a warning that says to drop the quotes, and given an unknown word in a kind position then parsing succeeds and the word is left for name resolution'
bound = false
+++

Implements grl-spec.md sections 4 and 5.

Recursive-descent parser for the section 5 grammar. The grammar is closed but the vocabulary is generated, so an unknown kind or verb parses and is rejected later as GRL001.
