---
id: T-1141
title: 'arch: abstraction-opportunity gate-rule-protocol detector exclusion (T-1114
  residue)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense gate/rule-builder convention rationale into T-1141 body
  actor: logan
  at: '2026-09-19'
  old_length: 2759
  new_length: 4136
evidence:
- tests/unit/arch_suite/test_abstraction.py::TestGateRuleBuilderExclusion::test_violation_returning_group_not_flagged
- tests/unit/arch_suite/test_abstraction.py::TestGateRuleBuilderExclusion::test_non_violation_returning_group_still_flagged
- tests/unit/arch_suite/test_abstraction.py::TestGateRuleBuilderExclusion::test_return_type_membership_matches_all_three_shapes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-1114 (triage of the 29 gates/ abstraction-opportunity
findings T-1082 handed off, after T-1112's identical precedent for
src/frob/arch/**). One real extraction WAS made in T-1114's own land
(_debt_edges/_deprecated_edges/_waive_edges consolidated behind a
shared frob.gates._edges_of_kind helper) -- but the ARCH gate's
abstraction-opportunity detector is purely signature-shape-based, not
body-based, so that group still reports as "duplicated" even though
the real duplication is now gone; this ticket is about the remaining
count regardless of further code changes, mirroring T-1112 exactly:

1. The gate-rule-builder protocol itself: the overwhelming majority of
   remaining groups are literally every gate/rule function across
   gates/__init__.py sharing one of a handful of conventional shapes --
   `(GraphSnapshot) -> tuple[Violation, ...]` (11 members),
   `(Path, GraphSnapshot) -> tuple[Violation, ...]` (17 members),
   `(Path) -> tuple[Violation, ...]` (19 members), `(Path) -> list[Violation]`
   (17 members), `(GraphSnapshot) -> list[Violation]` (4 members),
   `(str, str) -> Violation` (5 members), `(str, int, str) -> Violation`
   (8 members), `(str) -> Violation` (3 members). This is the package's
   own intentional common interface (every gate/rule builder returns
   Violation(s) this way), not duplicate logic -- the exact same "protocol
   family" shape T-1112 already carved out for src/frob/arch/**'s
   `check_*` detector registry.
2. Small genuinely-coincidental utility collisions: `_baseline.py`'s
   6-member `(Path) -> dict | None` group (load_baseline/
   load_coverage_lock/load_stamp/_read_toml x3 -- distinct config
   surfaces that happen to return the same optional-dict shape),
   `_gate_cache.py`'s sqlite connection openers (readonly vs readwrite
   variants, deliberately separate), `_waive_lease.py`'s 4 lease-
   lifecycle operations, `_pii_structural/_env_access.py`'s ast-node
   predicate/extractor helpers (tree-walk predicates coincidentally
   sharing a generic ast-node signature, the same class-4 "large mixed-
   concern tree-walk" shape T-1112 already named for src/frob/arch/**).
3. `_docblocks.py`/`_render_lint.py`'s tracked-file variants and
   `_fmt_directives.py`'s relpath helpers: plausible small dedup
   candidates but out of T-1114's own remaining budget to verify body-
   for-body; worth a follow-up look but not blocking this filing.

Generalize frob.arch._python._check_abstraction_opportunities's
exclusion mechanism (already proposed for the check_* registry family
in T-1112) to also recognize a package's own established gate/rule-
builder return-type convention, so this class of finding does not need
re-triaging by hand every time a gates/ split ticket re-measures.

<!-- narrative-moved:src/frob/arch/_abstraction.py:361:T-1141 -->
: `frob.gates`'s own gate/rule-builder return-type convention (T-1141,
: filed from T-1114 as the mirror of T-1112's `check_*` registry
: exclusion): every gate function (`*_gate`) and every rule-builder
: helper it dispatches to (`_tick001_duplicate_ids`, `_cov001`,
: `_test006`, `_inv005`, and dozens of siblings across gates/__init__.py
: and its `_*.py` split modules) returns one of these three shapes --
: `Violation`, `list[Violation]`, or `tuple[Violation, ...]` -- because
: `Violation` is `frob.gates`'s own domain type: nothing outside the
: gates package constructs one. A shared return type built entirely from
: `Violation`/collections of it is therefore the intentional common gate/
: rule-builder contract this package registers every check through, the
: same shape `_is_check_registry_family` already carves out for
: `frob.arch`'s own `check_*`/`run_*_checks` convention -- not duplicate
: logic, regardless of how many members happen to share it or what they
: are individually named (a structural discriminator, mirroring
: `_is_language_parity_family`'s per-language tag check, rather than a
: name-pattern one like `_is_check_registry_family`'s, since gate/rule-
: builder names do not share one fixed prefix/suffix convention the way
: `check_*`/`run_*_checks` do).
frob:ticket T-1195