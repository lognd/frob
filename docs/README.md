# Documentation index

Status: current
Owner: frob
Decisions: none
Audience: user

This is the one index of every document under docs/. Notes (frozen research and audits) are indexed in [notes/README.md](../notes/README.md). Each hand-written document starts with a header block (Status, Owner, Decisions, Audience) in this vocabulary:

- `current`: decided and, where it names code, built.
- `draft`: decided or proposed but not (fully) built, or still under review.
- `superseded-by X`: replaced by X; deleted in a later consolidation phase.
- `historical`: kept as a record; nothing new is built from it.
- `generated`: written by a generator named on its first line and checked by `cargo dev gen --check`; it carries the generator marker instead of a header block and is never edited by hand.

`current*` means the document is current but its header block is still to be added (follow-up ticket); until then this index is its status record.

## For users

| Document | Title | Status | Owner |
|---|---|---|---|
| [crunk/README.md](crunk/README.md) | crunk | current | crunk |
| [crunk/config.md](crunk/config.md) | crunk.toml reference | generated | crunk |
| [guides/quickstart.md](guides/quickstart.md) | Quickstart: from `frob init` to a landed ticket | current | frob |
| [guides/upgrade-from-v1.md](guides/upgrade-from-v1.md) | Upgrade from frob v1 to v2 | current | frob |
| [reference/cli/any.md](reference/cli/any.md) | `any` commands | generated | frob |
| [reference/cli/frob.md](reference/cli/frob.md) | `frob` commands | generated | frob |
| [reference/config.md](reference/config.md) | Configuration reference | generated | frob |
| [reference/directives.md](reference/directives.md) | Directives | generated | frob |
| [reference/fidelity.md](reference/fidelity.md) | Fidelity accounting | current | frob |
| [reference/languages.md](reference/languages.md) | Languages | generated | frob |
| [reference/tool-stages.md](reference/tool-stages.md) | Tool stages (`[[check.tool]]`) | current | frob |
| [reference/rules/](reference/rules/) | One page per check rule (86 pages) | generated | frob |

## For rule and model authors

| Document | Title | Status | Owner |
|---|---|---|---|
| [crunk/rules/README.md](crunk/rules/README.md) | crunk rules | generated | crunk |
| [design/cohesion.md](design/cohesion.md) | Function cohesion ("one job per function"), type precision and directive admission (D118-D121) | draft | grimble |
| [design/grl-spec.md](design/grl-spec.md) | GRL: the grimble rule language | draft | grimble |
| [design/grmb-spec.md](design/grmb-spec.md) | The .grmb language specification (G01) | draft | grimble |
| [design/neatness.md](design/neatness.md) | Neatness: the NEAT rule family | draft | grimble |
| [design/rule-authoring.md](design/rule-authoring.md) | Rule authoring: one rule, two files, compile errors first (D107) | current | gob |
| [design/testing.md](design/testing.md) | Testing rules against the universal model (D106) | current | gob |

## For contributors and agents

| Document | Title | Status | Owner |
|---|---|---|---|
| [design/README.md](design/README.md) | frob v2 design: file index and the decision log (D1-D133) | current | frob |
| [design/architecture.md](design/architecture.md) | Architecture: workspace, data flow, errors, logging | current | gob |
| [design/binding.md](design/binding.md) | Binding semantics over U (G02) | draft | grimble |
| [design/boundaries.md](design/boundaries.md) | Boundaries: what belongs to frob, grimble, crunk, and the shared substrate | current | gob |
| [design/build-test-ci.md](design/build-test-ci.md) | Build, test, docs generation, CI | current | frob |
| [design/cicd.md](design/cicd.md) | CI/CD and deployment languages | draft | grimble |
| [design/cli.md](design/cli.md) | CLI contract and verb surface | current | frob |
| [design/code-model.md](design/code-model.md) | Code model, symbolic binding, and the directive DSL | current | gob |
| [design/crunk.md](design/crunk.md) | crunk: an agent-first design tool where every interface is batch-checkable (D108-D117) | draft | crunk |
| [design/diagnostics.md](design/diagnostics.md) | Diagnostics that teach, and fixes that are safe to apply | current | gob |
| [design/doc-consistency.md](design/doc-consistency.md) | Doc consistency: one source, paired sections, checked facts | draft | frob |
| [design/documentation.md](design/documentation.md) | Documentation: what is written, what is generated, and where rationale lives | current | gob |
| [design/dotnet-unity.md](design/dotnet-unity.md) | C#, .NET and Unity support (D94) | current | grimble |
| [design/exceptions.md](design/exceptions.md) | Exceptions: waivers, debt, quick fixes, and permanent decisions | current | gob |
| [design/git-io.md](design/git-io.md) | Git and GitHub without subprocess storms | current | gob |
| [design/grimble-model.md](design/grimble-model.md) | grimble: the system-design model and its code binding | draft | grimble |
| [design/grmb-planning.md](design/grmb-planning.md) | The .grmb planning layer | draft | grimble |
| [design/gui.md](design/gui.md) | Stateless GUI | draft | frob |
| [design/language-engines.md](design/language-engines.md) | Language engines: what lives in gob, what lives in a product (D96) | current | gob |
| [design/migration.md](design/migration.md) | Migration from v1 and rollout | draft | frob |
| [design/mirror.md](design/mirror.md) | Ticket branch and the one-way tracker mirror | current | frob |
| [design/models/mirror/README.md](design/models/mirror/README.md) | Formal model of the one-way ticket mirror | current | frob |
| [design/monorepo.md](design/monorepo.md) | Monorepo: frob, grimble and crunk in one workspace | current | gob |
| [design/navigation.md](design/navigation.md) | Navigation: canonical ids, a verifiable reindex, generated docs, profiles and a tour | current | frob |
| [design/packs.md](design/packs.md) | Data packs and the registry drift-lock (G04) | draft | grimble |
| [design/paths.md](design/paths.md) | Paths: one discipline from type to lint (D86) | draft | gob |
| [design/plugins.md](design/plugins.md) | Plugins: one mechanism for the standard library and third parties | draft | gob |
| [design/pm-enforcement.md](design/pm-enforcement.md) | Enforcing project management | current | frob |
| [design/products.md](design/products.md) | Product split: three goblins, one workspace | current | gob |
| [design/releases.md](design/releases.md) | Releases: a scrumban flow wired to milestones, cycles and incremental releases | current | frob |
| [design/rules.md](design/rules.md) | Rules, gates, and the check pipeline | current | gob |
| [design/security.md](design/security.md) | Security of packs, plugins, tool stages and the mirror | current | gob |
| [design/sibling-contract.md](design/sibling-contract.md) | The sibling JSON contract (G03) | current | gob |
| [design/tickets.md](design/tickets.md) | Tickets: the project-management core | current | frob |
| [design/time.md](design/time.md) | Time: one clock, one zone, from type to lint (D93) | draft | gob |
| [design/tool-binding.md](design/tool-binding.md) | Tool binding: bind before own (D122) | draft | gob |
| [design/universal-model.md](design/universal-model.md) | The universal structural model (gob-ir) | current | gob |
| [migration/v1-import.md](migration/v1-import.md) | v1 ticket import | historical | frob |
| [reference/changelog.md](reference/changelog.md) | Changelog fragments | current | frob |

## For the owner

| Document | Title | Status | Owner |
|---|---|---|---|
| [decisions/2026-10-03-release-workflow-hand-written.md](decisions/2026-10-03-release-workflow-hand-written.md) | Release workflow is hand-written around `dist build` | current | frob |
| [design/goals.md](design/goals.md) | frob v2: goals and principles | current | gob |
| [guides/release.md](guides/release.md) | Cut a release | current | frob |

## Machine-readable and supporting files

- [schemas/](schemas/): JSON Schemas written by `cargo dev gen` (config, directives, envelope, sibling, crunk); generated.
- [assets/](assets/): images used by README.md.
- [design/models/mirror/](design/models/mirror/): the TLA+ model of the ticket mirror (see its README).
