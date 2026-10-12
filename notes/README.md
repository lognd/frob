# notes/ index

Status: current
Owner: frob
Decisions: none
Audience: owner

Notes are evidence: research, audits and v1 inventories that fed a design decision. docs/ is
normative; a note is never edited after its decision lands. This index has one row per note.
Date is the day the note was first committed. Status is `historical` (the decision it fed has
landed, the note is frozen), `current` (still the working reference for open work) or
`superseded-by X`. The documentation index is [docs/README.md](../docs/README.md).

## Top level

| Note | Date | Question | Decision fed | Status |
|---|---|---|---|---|
| [audit-design.md](audit-design.md) | 2026-10-02 | Do the 17 first design files agree with the v1 inventories? (67 findings) | D23-D37 | historical |
| [audit-resolution.md](audit-resolution.md) | 2026-10-02 | How was each finding of audit-design.md closed? | D23-D37 | historical |
| [coordinator.md](coordinator.md) | 2026-10-02 | Coordinator ground rules and state log (stops 2026-10-07) | none | superseded-by docs/guides/agents.md (planned; file deleted in the notes-archive phase) |
| [crunk.md](crunk.md) | 2026-10-02 | What is the Python crunk, and what carries over to the Rust workspace? | D28, D97 | historical |
| [documentation.md](documentation.md) | 2026-10-02 | How do mature Rust tools document themselves; where does rationale live? | docs/design/documentation.md | historical |
| [jira.md](jira.md) | 2026-10-02 | Jira data model, pinch points and agentic use as a reference for tickets | docs/design/tickets.md | historical |
| [perf-warm-check.md](perf-warm-check.md) | 2026-10-03 | Where does a warm `frob check` spend time (~A8AMNGF)? | none | historical |
| [rust-ecosystem.md](rust-ecosystem.md) | 2026-10-02 | Which Rust crates carry the workspace (versions checked 2026-10-01)? | D1 | historical |

## research/

| Note | Date | Question | Decision fed | Status |
|---|---|---|---|---|
| [calculi.md](research/calculi.md) | 2026-10-02 | Which calculi and universal cores can a structural model rest on? | D56 | historical |
| [cicd-survey.md](research/cicd-survey.md) | 2026-10-02 | What do the most used projects do in CI/CD, and what should frob lint? | D60 | historical |
| [codegen-macros.md](research/codegen-macros.md) | 2026-10-06 | How do mature Rust linters use codegen and macros? | D107 | historical |
| [creators-games-2026-10-08.md](research/creators-games-2026-10-08.md) | 2026-10-08 | Practitioner corpus for lint evidence: games, Unity C#, game UX | lint-catalogue-2026-10-08.md | historical |
| [creators-systems-2026-10-08.md](research/creators-systems-2026-10-08.md) | 2026-10-08 | Practitioner corpus for lint evidence: systems languages and architecture | lint-catalogue-2026-10-08.md | historical |
| [creators-web-2026-10-08.md](research/creators-web-2026-10-08.md) | 2026-10-08 | Practitioner corpus for lint evidence: front end | lint-catalogue-2026-10-08.md | historical |
| [crunk-design-2026-10-08.md](research/crunk-design-2026-10-08.md) | 2026-10-08 | What should an agent-first design tool look like? | D108-D117 | historical |
| [crunk-sources-2026-10-08.md](research/crunk-sources-2026-10-08.md) | 2026-10-08 | Sourcing pass for crunk-design-2026-10-08.md | D108-D117 | historical |
| [deslop-research-2026-10-08.md](research/deslop-research-2026-10-08.md) | 2026-10-08 | What marks generic front-end output, and what can crunk check? | D108-D117 | historical |
| [docgen-survey.md](research/docgen-survey.md) | 2026-10-03 | How do repositories generate and single-source documentation? | D84 | historical |
| [docs-survey.md](research/docs-survey.md) | 2026-10-02 | How do 1254 popular repositories document themselves? | D81, D84 | historical |
| [grmb-r2-faults.md](research/grmb-r2-faults.md) | 2026-10-09 | Ambient faults and exhaustive error handling for grmb (R2, topic H) | D124-D133 | current |
| [grmb-r2-verification.md](research/grmb-r2-verification.md) | 2026-10-09 | Verification and traceability practice for the grmb level pairing (R2, topic G) | D124-D133 | current |
| [lint-catalogue-2026-10-08.md](research/lint-catalogue-2026-10-08.md) | 2026-10-08 | Evidence-weighted synthesis of the lint evidence study | D118-D121 | historical |
| [lint-evidence-study.md](research/lint-evidence-study.md) | 2026-10-08 | Design of the lint evidence study | D118-D121 | historical |
| [lint-requirements.md](research/lint-requirements.md) | 2026-10-02 | Which queries must a universal IR answer for every rule family? | D56 | historical |
| [lint-reuse-research-2026-10-08.md](research/lint-reuse-research-2026-10-08.md) | 2026-10-08 | Can frob reuse existing linters instead of re-implementing them? | D122 | historical |
| [mining-report-2026-10-08.md](research/mining-report-2026-10-08.md) | 2026-10-08 | What do review comments and refactors in 1005 repositories show? | D118-D121 | historical |
| [neatness.md](research/neatness.md) | 2026-10-02 | What should a NEAT rule family check over the universal model? | D59 | historical |
| [paradigms.md](research/paradigms.md) | 2026-10-02 | What structure must a model carry to cover 202 languages? | D56 | historical |
| [plugins.md](research/plugins.md) | 2026-10-02 | Which plugin mechanism and tier choice fits frob and grimble? | D76 | historical |
| [profile-2026-10-07.md](research/profile-2026-10-07.md) | 2026-10-08 | How long does every leaf command of the three binaries take? | none | historical |
| [reading-list.md](research/reading-list.md) | 2026-10-02 | Reading path on language design and the mathematics of languages | none | current |
| [rule-authoring.md](research/rule-authoring.md) | 2026-10-06 | How does adding a rule work today, and what is the simplest design? | D107 | historical |
| [rule-languages.md](research/rule-languages.md) | 2026-10-02 | What should GRL copy from 17 rule systems, and avoid? | D80 | historical |
| [rule-testing.md](research/rule-testing.md) | 2026-10-06 | How do mature Rust linters test rules? | D103, D106 | historical |
| [u-testing-audit.md](research/u-testing-audit.md) | 2026-10-06 | Does the rule-testing model fit the three-valued universal model? | D106 | historical |

## review/

| Note | Date | Question | Decision fed | Status |
|---|---|---|---|---|
| [adoption-trial-2026-10-07.md](review/adoption-trial-2026-10-07.md) | 2026-10-08 | What breaks when a newcomer adopts the 0.532.0 debug binary? | none | historical |
| [audit-2026-10-07.md](review/audit-2026-10-07.md) | 2026-10-07 | Structural audit: crate graph, correctness risks, CI, drift | none | historical |
| [design-consistency.md](review/design-consistency.md) | 2026-10-02 | Is the design set consistent after the U, NEAT, CI/DK and grimble drafts? | D61-D64 | historical |
| [design-consistency-resolution.md](review/design-consistency-resolution.md) | 2026-10-02 | How were the findings of design-consistency.md resolved? | D61-D64 | historical |
| [design-consistency-2.md](review/design-consistency-2.md) | 2026-10-03 | Fifteen contradictions found while decomposing D76 and D78-D84 | D85 | historical |
| [formal-review-2026-10-08.md](review/formal-review-2026-10-08.md) | 2026-10-08 | Referee review of the universal model and GRL | none | historical |
| [grimble-review.md](review/grimble-review.md) | 2026-10-02 | Is grimble thought out end to end against the universal model? | D61-D64 | historical |
| [mirror-audit.md](review/mirror-audit.md) | 2026-10-03 | Does reconcile-by-field-ownership hold against GitHub Issues? | D79 | historical |
| [plugin-security-audit.md](review/plugin-security-audit.md) | 2026-10-02 | What can go wrong in the plugin and pack system? (34 findings) | D82 | historical |
| [trust-ux-audit.md](review/trust-ux-audit.md) | 2026-10-02 | How should the human trust step for packs and tool stages work? | D82 | historical |
| [v1-gap/README.md](review/v1-gap/README.md) | 2026-10-04 | Index of the v1 to v2 gap analysis | none | historical |
| [v1-gap/A-keep-recommendations.md](review/v1-gap/A-keep-recommendations.md) | 2026-10-04 | Is every v1 KEEP or MERGE recommendation built, ticketed or dropped? | none | historical |
| [v1-gap/B-backlog.md](review/v1-gap/B-backlog.md) | 2026-10-04 | What do the 970 open v1 tickets mean for v2? | none | historical |
| [v1-gap/C-features.md](review/v1-gap/C-features.md) | 2026-10-04 | Which v1 features (MCP, daemon, editors, fleet, ...) are covered in v2? | none | historical |
| [v1-gap/D-incidents.md](review/v1-gap/D-incidents.md) | 2026-10-04 | Which v1 failure classes can recur in v2? (45 classes) | none | historical |
| [v1-gap/E-triage.md](review/v1-gap/E-triage.md) | 2026-10-04 | Triage summary of 387 v1 tickets | none | historical |

## v1/

| Note | Date | Question | Decision fed | Status |
|---|---|---|---|---|
| [agent-usage.md](v1/agent-usage.md) | 2026-10-02 | How did agents and the human actually use v1? | D1-D22 | historical |
| [cli-surface.md](v1/cli-surface.md) | 2026-10-02 | What is the v1 CLI surface (243 parser nodes)? | docs/design/cli.md | historical |
| [gates-and-rules.md](v1/gates-and-rules.md) | 2026-10-02 | Which v1 gates and rules exist and which carry over? | docs/design/rules.md | historical |
| [graph-lang-dsl.md](v1/graph-lang-dsl.md) | 2026-10-02 | What are the v1 obligation graph, language layer and comment DSL? | docs/design/code-model.md | historical |
| [ops-and-integrations.md](v1/ops-and-integrations.md) | 2026-10-02 | What are v1's ops, integrations, config and performance evidence? | docs/design/architecture.md | historical |
| [strata.md](v1/strata.md) | 2026-10-02 | What is strata (v1) and what becomes grimble? | docs/design/products.md | historical |
| [tickets.md](v1/tickets.md) | 2026-10-02 | What is the v1 ticket subsystem? | docs/design/tickets.md | historical |
