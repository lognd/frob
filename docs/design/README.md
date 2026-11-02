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
| ../history/milestones.md | HISTORICAL: the milestone 1 and 2 plans, the early workspace tree, and the old file-to-product move table |
| frob/tickets.md | ledger, ids, data model, links, workflow, leases, evidence, landing, Jira mapping; the ticket branch layout and the one-way tracker mirror (credentials, partial failure, rate limits, identity, tracker edits, schema drift, downtime) |
| code-model.md | symbols, symref grammar, digests and lock mechanics, adapters, directive DSL (including milestone-2 claim directives), cross-language binds, capability matrix pointer; section 5 (structural IR) is a pointer to universal-model.md |
| rules.md | rule derive, families, check pipeline, waivers, ratchet |
| build-test-ci.md | build locality, test kinds, generated artifacts, CI budget |
| grimble-capabilities-v3.md | v3 capability language: typed atom arguments, symbol-scoped grants and providers, effect transitivity, never-claims, taint, expiring exceptions, profiles, vocabulary versioning |
| migration.md | v1 import, rule id map, rollout |
| frob/pm-and-releases.md | structured user stories, definition of ready/done, velocity-aware cycles, measured forecasts, WIP; releases: a scrumban flow wired to milestones, cycles and incremental releases |
| exceptions.md | accept / defer / hotfix / baseline with machine-checkable exits, budgets, reason quality, EXC rules, migration of v1 waivers |
| documentation.md | one home per kind of knowledge, generated vs written pages, NARR rules that keep ticket narrative out of code, ADRs, changelog fragments, rustdoc discipline |
| output.md | DRAFT: pretty TTY output: the `frob-present` crate boundary, TTY/NO_COLOR/CI detection, palette, presenter trait and stage-event model, routing all human output through logging, JSON envelope unchanged |
| plugins.md | DRAFT for owner review: one pack mechanism for the standard library and third parties; tiers (data, declarative plans, WASM code rules, adapters), universal versus single-language rules, pytest-style typed hooks, performance parity by one executor and benchmark gates, excuses as pack data |
| universal-model.md | DRAFT, D56 accepted: the universal structural model U (sorted ABTs, scope graph with Must/May/Unknown, opaque, provenance), totality / adequacy / honesty theorems, answer lattice and rule polarity, 47-query interface, paradigm coverage, gaps in landed code |
| grimble/grmb-spec.md | DRAFT, G01 plus the planning layer: the one .grmb language specification (lexical rules and the one keyword table, `use` and versioning, the eight architecture entities and their fields, names and scoping, the selector grammar and owner function, exceptions and the debt key set, directives and the one evidence clause `verified_by`, the F4 U encoding, the binding relation; the planning layer: systems, actors, goal variant sets, steps with typed outcomes, scenarios with exhaustive arms, impls with waypoint chains and outcome maps, pages, the derived V-model, ambient faults, `sorry`, `unknown`, `one_of`; every rule table (MDL, PLAN, SYS015/016, AMB, PM037-043); graph JSON and the frob join; one example; the one open-questions list). Evidence: notes/research/grmb-evidence/ |
| grimble/binding.md | DRAFT, G02: binding semantics over U (the relation B with roles and provenance, the four ranked sources and their merge and conflict rules, SCIP and LSP occurrences, the twelve v1 mechanisms mapped, identity and rename over commits, SYS001-SYS012 as predicates with polarity and Unresolved conditions, the capability matrix as a view over B, the gob-walk and gob-ir queries, worked examples, conformance corpus) |
| grimble/rule-families.md | DRAFT, D59 D60 D118 D120 D121: the NEAT, COH, and CI/DK rule families (purpose, rules, knobs, decided, open), merged from the old neatness, cohesion and cicd docs |
| sibling-contract.md | DRAFT, G03: the sibling `--json` contract (invocation and exit codes, the `gob.sibling/1` document with fidelity, findings, polarity, required mark, exceptions with opaque tickets, entities and bindings, the `grimble.graph/1` export, version negotiation, frob's merge rules, the absent and incompatible cases, budget and security), with docs/schemas/sibling.json |
| packs.md | DRAFT, G04: data packs (the TOML pack format with atoms, detectors by kind, callee vocabularies, inference rules, claim templates and a JSON Schema outline; built-in, repository and external sources; the `grimble.packs.lock` drift-lock with item-wise PACK001 findings and the explicit `grimble packs update`; materialization; detectors to matrix cells and the `impossible` declaration of not-applicable; the compute-digest decision; the three milestone-2 packs `core-effects`, `ci-github`, `rust-ecosystem`; PACK001-008) |
| dotnet-unity.md | ACCEPTED DIRECTION, D94: first-party C# adapter, the .NET and Unity project model (.csproj, .asmdef), an opt-in `unity` vocabulary pack (engine entry points as reach roots, serialized fields, dynamic calls, .meta hygiene), and `dotnet` and `unity` evidence providers |
| language-engines.md | ACCEPTED DIRECTION, D96: the placement rule (facts about what is written live in gob, domain judgements in products), four more universal capabilities (`markup`, `style`, `const_value`, `project_model`), gob-frameworks for routes and entry points, and the placement of every TS/TSX/JSX/CSS item |
| testing.md | ACCEPTED DIRECTION, D106: how rule tests observe U: outcome classes, certified clean, required cases per polarity and tier, the language matrix, measured fidelity, U-aware fix and snapshot invariants |
| rule-authoring.md | ACCEPTED DIRECTION, D107: one rule is two colocated files with a fully required `#[rule]` attribute and `applies`, one applicability resolver over the gob-caps matrix, generated rule indexes with compile-time uniqueness, and the new-rule scaffold |
| crunk.md | ACCEPTED DIRECTION, D108-D117: crunk as an agent-first design tool: text sources under design/ (DTCG tokens with modes, component, screen, flow, content and profile specs, a restricted HTML/CSS scene dialect), check tiers T0-T4, taffy solve plus Playwright render with a parity test, agent verbs (new, edit --patch, render, diff, export, serve), lint families incl. GX, a human review lock (crunk.lock, Advisory in CI, blocking at release), the design-cycle artifacts and the build order |
| tool-binding.md | ACCEPTED DIRECTION, D122: bind before own: single-language rules come from maintained tools run as pinned subprocesses (SARIF or native JSON, source_rule kept, native config read never rewritten, tool-owned fixes and suppressions audited by EXC017); tool definitions are data (pins, version-ranged commands, exit classes, id maps); oxlint the JS/TS default; type facts through ty server and a TypeScript helper |
