# frob v2 design

Status: current
Owner: frob
Decisions: none
Audience: contributor

Design-first rewrite of frob in Rust. Start with shared/charter.md, then
shared/architecture.md and shared/cli-contract.md, then the rest. Decisions and their
precedence are in [the decision log](../decisions/README.md); each file
below carries the records it owns under its `Decision records` heading.

| File | Covers |
|---|---|
| shared/charter.md | the one charter: goals, non-goals, principles; the frob / grimble / crunk product split and the one placement test; the monorepo layout and publishing; boundaries, the one crate table, naming and dependency rules |
| shared/architecture.md | workspace layering, data flow, storage, errors, logging, config, agent surface; in-process git via gix, bounded spawns, GitHub over HTTPS; the path and time disciplines (D86, D93) |
| shared/cli-contract.md | verb surface, JSON envelope, exit codes, idempotency, jobs; diagnostics that teach and fix applicability; the stateless web GUI and TUI over the same handlers |
| shared/code-model.md | symbols, symref grammar, digests and lock mechanics, the directive DSL, cross-language binds, the capability matrix pointer, and one adapter chapter per language (Rust, Python, TypeScript, C#/.NET and Unity), including the language-engine placement rule (D96, D94) |
| shared/universal-model.md | D56 accepted: the universal structural model U (sorted ABTs, scope graph with Must/May/Unknown, opaque, provenance), totality / adequacy / honesty theorems, answer lattice and rule polarity, 47-query interface, paradigm coverage, gaps in landed code |
| shared/rules.md | rule derive, families, check pipeline, waivers, ratchet; exceptions (accept / defer / hotfix / baseline); rule authoring; one chapter on testing a rule (outcome classes, fix harness, ecosystem check); tool binding (D122) |
| shared/build-test-ci.md | build locality, test kinds, generated artifacts, CI budget, release and CI across the three products |
| shared/packs-and-plugins.md | one extension mechanism: tiers (data, declarative plans, WASM code rules, adapters), data packs and the drift-lock (PACK001-008), the three milestone-2 packs, performance parity |
| shared/security.md | security of packs, plugins, tool stages and the mirror (D82), with the policy snapshot |
| shared/documentation.md | one home per kind of knowledge, generated vs written pages, NARR rules, ADRs, changelog fragments, rustdoc discipline, doc consistency and the navigation contract |
| shared/sibling-contract.md | G03: the sibling `--json` contract (the `gob.sibling/1` document, `grimble.graph/1` export, version negotiation, merge rules, absent and incompatible cases), with docs/schemas/sibling.json |
| shared/grl-spec.md | GRL, the grimble rule language, with its worked examples and model |
| ../history/milestones.md | HISTORICAL: the milestone 1 and 2 plans, the early workspace tree, and the old file-to-product move table |
| frob/tickets.md | ledger, ids, data model, links, workflow, leases, evidence, landing, Jira mapping; the ticket branch layout and the one-way tracker mirror (credentials, partial failure, rate limits, identity, tracker edits, schema drift, downtime) |
| grimble/grimble-capabilities-v3.md | v3 capability language: typed atom arguments, symbol-scoped grants and providers, effect transitivity, never-claims, taint, expiring exceptions, profiles, vocabulary versioning |
| frob/migration.md | v1 import, rule id map, rollout |
| frob/distributed-tickets.md | many people and agents on one ledger: claims, leases, freshness probe, refresh and sync policy, land divergence |
| frob/pm-and-releases.md | structured user stories, definition of ready/done, velocity-aware cycles, measured forecasts, WIP; releases: a scrumban flow wired to milestones, cycles and incremental releases |
| frob/output.md | DRAFT: pretty TTY output: the `frob-present` crate boundary, TTY/NO_COLOR/CI detection, palette, presenter trait and stage-event model, routing all human output through logging, JSON envelope unchanged |
| grimble/grmb-spec.md | DRAFT, G01 plus the planning layer: the one .grmb language specification (lexical rules and the one keyword table, `use` and versioning, the eight architecture entities and their fields, names and scoping, the selector grammar and owner function, exceptions and the debt key set, directives and the one evidence clause `verified_by`, the F4 U encoding, the binding relation; the planning layer: systems, actors, goal variant sets, steps with typed outcomes, scenarios with exhaustive arms, impls with waypoint chains and outcome maps, pages, the derived V-model, ambient faults, `sorry`, `unknown`, `one_of`; every rule table (MDL, PLAN, SYS015/016, AMB, PM037-043); graph JSON and the frob join; one example; the one open-questions list). Evidence: notes/research/grmb-evidence/ |
| grimble/binding.md | DRAFT, G02: binding semantics over U (the relation B with roles and provenance, the four ranked sources and their merge and conflict rules, SCIP and LSP occurrences, the twelve v1 mechanisms mapped, identity and rename over commits, SYS001-SYS012 as predicates with polarity and Unresolved conditions, the capability matrix as a view over B, the gob-walk and gob-ir queries, worked examples, conformance corpus) |
| grimble/rule-families.md | DRAFT, D59 D60 D118 D120 D121: the NEAT, COH, and CI/DK rule families (purpose, rules, knobs, decided, open), merged from the old neatness, cohesion and cicd docs |
| dup.md | DRAFT: duplicate-code tiers (clone detection) and their cost |
| models/mirror/README.md | formal TLA+ model of the one-way ticket mirror (Mirror.tla, MirrorRace.tla, TLC configs) and its findings |
| grimble/output-atoms.md | DRAFT: output atoms, every way a program writes per language; the `toml output-atoms` and `toml output-languages` catalogue the LOG001 rule loads |
| crunk/crunk.md | ACCEPTED DIRECTION, D108-D117: crunk as an agent-first design tool: text sources under design/ (DTCG tokens with modes, component, screen, flow, content and profile specs, a restricted HTML/CSS scene dialect), check tiers T0-T4, taffy solve plus Playwright render with a parity test, agent verbs (new, edit --patch, render, diff, export, serve), lint families incl. GX, a human review lock (crunk.lock, Advisory in CI, blocking at release), the design-cycle artifacts and the build order |
