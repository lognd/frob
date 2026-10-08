+++
id = "01M4CTTQFF84AWJZKH89X572Y1"
title = "README for v2 and a getting-started guide (init to land) plus a command reference generated from the CLI"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:34Z"
updated = "2026-10-08T04:04:45Z"
labels = ["creates:crates/frob/tests/doc_commands.rs"]
scope = ["changelog.d/**", "README.md", "docs/guides/**", "crates/frob/tests/doc_commands.rs"]

[[acceptance]]
text = "Given the README, when every command it shows is run in a fresh repository, then each is a v2 verb that succeeds (doc test)"
bound = false

[[acceptance]]
text = "Given every link in README.md and docs/guides, when checked, then each target exists"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md HIGH 1: README is v1 (frob graph build, --kind, T-0001), advertises serve/vet/agent/scaffold, links docs/guides/quickstart.md and command-reference.md that do not exist. Write a v2 README, docs/guides/quickstart.md (the loop the trial pieced together: init, ticket new, cycle, work, test, evidence, check --ticket, land, board, release), and generate docs/reference/cli.md from the clap trees through cargo dev gen (GEN001 keeps it current) if not already generated elsewhere.
