+++
id = "01M4H0WZ6Z1MDH6G815EE8MASY"
title = "Docs index and status headers: docs/README.md and notes/README.md, one header block on every docs file, stale facts fixed"
type = "docs"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:37Z"
updated = "2026-10-09T21:34:46Z"
idempotency_key = "docs-consolidation-2026-10-09-p1"
labels = ["creates:docs/README.md", "creates:notes/README.md"]
scope = [".github/PULL_REQUEST_TEMPLATE.md", "README.md", "changelog.d/01M4H0WZ6Z1MDH6G815EE8MASY*", "crates/frob-worktree/src/lib.rs", "crates/gob-plan/README.md", "docs/README.md", "docs/crunk/README.md", "docs/decisions/2026-10-03-release-workflow-hand-written.md", "docs/design/architecture.md", "docs/design/binding.md", "docs/design/boundaries.md", "docs/design/cicd.md", "docs/design/code-model.md", "docs/design/cohesion.md", "docs/design/crunk.md", "docs/design/diagnostics.md", "docs/design/doc-consistency.md", "docs/design/dotnet-unity.md", "docs/design/exceptions.md", "docs/design/git-io.md", "docs/design/goals.md", "docs/design/grimble-model.md", "docs/design/grl-spec.md", "docs/design/grmb-planning.md", "docs/design/grmb-spec.md", "docs/design/gui.md", "docs/design/language-engines.md", "docs/design/migration.md", "docs/design/mirror.md", "docs/design/models/mirror/README.md", "docs/design/monorepo.md", "docs/design/neatness.md", "docs/design/packs.md", "docs/design/paths.md", "docs/design/plugins.md", "docs/design/pm-enforcement.md", "docs/design/products.md", "docs/design/releases.md", "docs/design/rule-authoring.md", "docs/design/rules.md", "docs/design/security.md", "docs/design/sibling-contract.md", "docs/design/testing.md", "docs/design/time.md", "docs/design/tool-binding.md", "docs/design/universal-model.md", "docs/guides/quickstart.md", "docs/guides/release.md", "docs/guides/upgrade-from-v1.md", "docs/migration/v1-import.md", "docs/reference/changelog.md", "docs/reference/fidelity.md", "docs/reference/tool-stages.md", "notes/README.md", "notes/coordinator.md", "notes/crunk.md", "notes/jira.md", "notes/research/cicd-survey.md", "notes/research/docgen-survey.md", "notes/research/docs-survey.md", "notes/research/rule-authoring.md", "notes/research/rule-languages.md", "notes/research/rule-testing.md", "notes/review/adoption-trial-2026-10-07.md", "notes/review/trust-ux-audit.md", "notes/v1/agent-usage.md", "notes/v1/cli-surface.md", "notes/v1/gates-and-rules.md", "notes/v1/graph-lang-dsl.md", "notes/v1/ops-and-integrations.md", "notes/v1/strata.md", "notes/v1/tickets.md", "docs/design/navigation.md", "docs/design/documentation.md"]

[[acceptance]]
text = "Given every markdown file under docs/, when phase 1 lands, then each starts with the Status/Owner/Decisions/Audience block of the report's section 3 principle 5 and docs/README.md lists every document by audience"
bound = true

[[acceptance]]
text = "Given notes/, when phase 1 lands, then notes/README.md has one row per note (date, question, decision fed, status)"
bound = true

[[acceptance]]
text = "Given the stale facts of report section 2.3, when phase 1 lands, then the 'tickets.md section 6' citations, the crunk and gob-plan READMEs, the PR template, the README typo, the fake 0.532.0 heading and the 17 absolute local paths are fixed, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 1 of notes/review/docs-consolidation-2026-10-09.md (sections 2.3, 3 principle 5). The header check itself is ~W5JD1VG. Folds in ~VQTPNVW (generated docs/README.md map) and ~XCH7F2D (docs/SUMMARY.md): close those as duplicates of this ticket.
