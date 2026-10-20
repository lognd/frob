+++
id = "01M1T07NWQRGSD3D4X76FV77F5"
title = "GEN001: declared-generated-files block plus drift gate"
type = "task"
category = "todo"
priority = "low"
parent = "01M1T07NWGXQV249M3HN5DQV9V"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3991"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/policy/__init__.py"]

[[acceptance]]
text = "given a design note for the declared-generated-files schema (source, generator command, output) and at least one candidate first-adopter case in this repo, when this ticket's design step completes, then the note is attached before implementation"
bound = false

[[acceptance]]
text = "given a declared generated-file entry whose generator output no longer matches the checked-in file, when the new gate runs, then GEN001 fires"
bound = false
+++

F-203 (T-3984 item 8). VERIFIED: git grep for GEN001 across src/frob found nothing -- no existing declared-generated-files construct or gate.

FINDING THIS WOULD HAVE CAUGHT: three hand-written drift tests, each independently re-verifying that a generated file matches its generator's current output, duplicating the same check-command-and-diff logic three times (the exact "two copies of a rule is a bug waiting to desync" shape this repo's own CLAUDE.md names). Proposed: a declared-generated-files block (source file -> generator command -> output file) plus one gate that runs each declared check command and diffs the result, replacing the three hand-written tests with one data-driven mechanism.

FIRST STEP: identify which three hand-written drift tests the consumer means is not directly determinable from our side (this is their repo's shape) -- so this ticket's first task is designing the declared-generated-files schema generically, then finding this repo's OWN analogous hand-written generated-file drift tests (if any) as a first adopter/proof of concept before rolling it out as a general frob feature.
