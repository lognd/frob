+++
id = "01M2Y1SS0EKZYRYS08596NPZJW"
title = "Remove ticket citations (T-####) from all user-facing help and docs: argparse help strings, docs/, refusal and remedy text"
type = "story"
flavour = "user_story"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M0XNVQXJ1A3FA43N7AA0PAPK"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5134"]
labels = ["milestone:1.0.0", "component:cli"]
scope = ["src/frob/_cli_parsers/*.py", "tests/unit/coordinator_suite/test_count_ticket_citations.py", "scripts/count_ticket_citations.py", "scripts/strip_help_citations.py", "docs/commands/ack.md", "docs/commands/clean.md", "docs/commands/doctor.md", "docs/commands/gitlog.md", "docs/commands/graph.md", "docs/commands/map.md", "docs/commands/mutate.md", "docs/commands/perf.md", "docs/commands/release.md", "docs/commands/serve.md", "docs/commands/status.md", "docs/commands/test.md", "docs/commands/vet.md", "docs/design/cwe-1000-registry.md", "docs/guides/command-reference.md", "docs/guides/editors.md", "docs/guides/extending/cve-fingerprints.md", "docs/guides/extending/design-lint-rules.md", "docs/guides/extending/failure-injection-acceptance-criteria.md", "docs/guides/extending/pii-categories.md", "docs/guides/extending/prover-claim-kinds.md", "docs/guides/extending/scenario-kinds.md", "docs/guides/extending/ticket-kinds-states.md", "docs/guides/frob-toml.md", "tests/unit/coordinator_suite/test_strip_help_citations.py", "docs/guides/coordinator-scripts.md"]

[[acceptance]]
text = "given the full CLI, when every 'frob ... --help' output is captured, then no output contains a T-#### token"
bound = false

[[acceptance]]
text = "given docs/ excluding docs/audits and the tickets tree, when scanned, then no prose line contains a T-#### token"
bound = false

[[acceptance]]
text = "given a new help= string containing T-1234, when frob check runs, then the DOC lint fires with the file and line"
bound = false
+++

Owner directive 2026-09-20: ticket prose (T-#### citations) is removed in its entirety from frob documentation and help. Measured: 462 T-#### mentions across src/frob/_cli_parsers/*.py alone (visible in every --help output, e.g. 'free-form sprint commitment label (e.g. 2026-W30, sprint-14, T-0715)'), plus the docs/ prose T-4422 (DOC012) already covers. Scope of THIS story: (1) argparse help/description/epilog strings in src/frob/_cli_parsers and any runner-side help text: strip the citation, keep the sentence, move any WHY worth keeping into the ticket ledger or a docs/design page; (2) refusal and remedy messages the user reads at the terminal (the 'T-2006 dropped N stale...' log lines are fine as INFO logs, but ERROR text and remedies must not cite tickets); (3) docs/ prose beyond T-4422's DOC012 scope: tables, headings, code-fence captions; (4) a lint so it cannot recur: extend DOC012 (or add DOC013) to fire on a T-#### token inside an argparse help= / description= string literal and inside docs/ prose outside the tickets ledger and docs/audits history; the ledger, done-reports, frob:ticket directive comments, commit messages and CHANGELOG remain the only homes for ticket ids. Coordinate with T-4422 (docs prose) and T-4691 (source comment narrative) so the three stories do not collide on the same files: this story owns _cli_parsers and user-facing message strings; T-4422 owns docs/ prose; T-4691 owns source comments.
