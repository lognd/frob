+++
id = "01M3AXSD9QFDKZBDV1NX4J7K69"
title = "GRAMMAR: module-level `owner STRING` declaration"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBEQGV8V5VHYGXBEQTV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:17Z"
aliases = ["T-6455"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["strata-core/src/parse/grammar_module.rs", "docs/strata/surface.md#module", "src/frob/strata/_models.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: module-level owner STRING declaration
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 2
scope: strata-core/src/parse/grammar_module.rs, docs/strata/surface.md#module,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/module-owner/**
blocked_by: [T-STORE-301-ATTR]

Finding (STRATA-EXPRESSIVENESS.md, section G "STRUCTURE"):

"`module` IS effectively a bounded context (a named, export-controlled unit), but there's no
explicit 'team X owns module Y' declaration -- ownership rides `Waiver.owner`/`Claim.owner` (a
person string on individual waivers/claims, _models.py:374,585) not on the module/node itself.
Proposal (GRAMMAR, minor): top-level or node_prop `owner STRING` clause, grammar_module.rs
(module-level) and/or grammar_node.rs (node-level), desugars to attr/typed field. Enables
RULE: a module with no declared owner and open `frob:waive` entries -- ownership-hygiene
check, authority: this repo's own existing Waiver.owner precedent generalized."

Node-level `owner` is covered by T-SYS-A-NODE-OPS; this leaf is the module-level half only
(different grammar file, genuinely scope-disjoint).

Acceptance criteria: grammar_module.rs gains a top-level `owner STRING` clause on `module { }`
blocks, desugars to attr, registered in T-STORE-301-ATTR's table. Positive-control fixture:
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
tests/fixtures/sysdesign/module-owner/module-no-owner-open-waiver/design.strata.
