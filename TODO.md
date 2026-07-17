# TODO

Superseded by tickets/ -- run: `frob ticket doable`

Phase 0-6 (alpha purge through frob.lang/frob.graph/frob.tickets/frob.gates
core, and the docs/release pass) are DONE; history lives in git, not here.
Remaining backlog now lives as tickets, one coherent item per ticket:

- T-0001 -- frob-core PyO3/maturin crate + smart dup (Phase 7)
- T-0002 -- frob.fuzz generators + FUZZ gates (Phase 8)
- T-0003 -- REL001 release gate: semver-correct version bump from graph digests
- T-0004 -- Decision records (ADR): decisions/AD-###.md + frob:decision edges
- T-0005 -- Ticket kind=incident with blameless-postmortem body template
- T-0006 -- Ticket acceptance field (given/when/then) verified by reviewer agent
- T-0007 -- STRIDE threat field on kind=security tickets
- T-0008 -- frob.vet: dependency capability vetting (docs/modules/vet.md build-out)
- T-0009 -- frob stats: DORA-ish measurement from gitlog + tickets
- T-0010 -- frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work
- T-0011 -- Mutation testing as the test-quality oracle
- T-0012 -- frob ticket renumber: remedy for sequential-id collisions
- T-0013 -- Raise min_unit_cases from 1 back to 3
- T-0014 -- Annotate legacy modules to flip COV001 back to error
- T-0015 -- Implement per-rule severity overrides in frob.toml
- T-0016 -- Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
- T-0017 -- Pair-level (consumer x provider) integration test obligations for TEST003
- T-0018 -- Convention-based unit-test binding inference to reduce frob:tests burden
