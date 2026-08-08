---
id: T-1198
title: 'strata: eliminate attr interface= boilerplate (4236 of 5588 frob.strata lines)
  via generated fragment or compact grammar'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/**
- design/**
- docs/**
- tests/**
- strata-core/src/parse/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: add
  glob: strata-core/src/parse/**
  reason: T-1198's grammar shorthand (attr interface=[...]) is implemented in strata-core's
    Rust parser, not just the Python side
  actor: logan
  at: '2026-08-03'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
designated_repro_test: null
acceptance:
- text: 'GIVEN the interface surface of a node WHEN it is machine-derivable (sync_interface
    already rewrites attr interface= lines to match code exactly) THEN the hand-authored
    .strata file no longer carries one line per symbol: either a generated .strata
    fragment (generate-and-verify like the rule registry) or a compact declaration
    form (list/module-ref) the parser accepts, design decides'
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- text: GIVEN the migration lands THEN frob check --only sys findings are diff-clean
    vs the inline-attr model and sync_interface round-trips idempotently on the new
    form
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
evidence_changes:
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_legacy_form_migrated_even_with_matching_symbol_set
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
threat: null
component: null
anchor: false
anchor_reason: null
---
User directive 2026-07-29: 4236 of design/frob.strata's 5588 lines are attr interface=<symbol> lines, one symbol per line, maintained mechanically by frob.strata._sync_interface (which loads every .strata file and rewrites the attrs to match code exactly). The hand-authored design intent drowns in generated-shaped noise. Candidate designs for the design note: (a) generated sidecar fragment design/frob.interface.strata written by sync_interface and verified by the SYS gate (T-1008 generate-and-verify precedent); (b) grammar shorthand attr interface=[a, b, ...] or interface from <module-path> resolved at parse time; (c) move interface bindings out of the surface file entirely into the code-binding layer. Coordinate with T-1196 (multi-file split) -- a generated fragment is itself a second file, so the cross-file semantics land first or together.

## Done report

Architecture decision (coordinated with T-1196): eliminate the
attr interface=<symbol>; one-line-per-symbol boilerplate (4236 of
design/frob.strata's 5588 pre-T-1198 lines) via a GRAMMAR SHORTHAND
(strata-core's parse_attrval, `attr interface=[Foo, Bar, Baz];`) rather
than a generated sidecar fragment. Both options were live; the grammar
shorthand won because it is pure parser sugar -- the bracket-list form
expands, at parse time, into the exact same per-symbol attr strings the
old form produced, so _elaborate.py, _selfconform.py's SYS104
measurement, and every gate reading Node.attrs needed ZERO changes. A
sidecar-fragment design would have needed the same zero read-side
changes but also a real decision about splitting node bodies across two
files (a materially bigger AST/grammar change) -- the grammar shorthand
sidesteps that by staying inside one node's own { ... } body.

Mechanism:
- strata-core/src/parse/lexer.rs: lexed `[`/`]` as symbols (not tokenized
  at all before this ticket).
- strata-core/src/parse/grammar_core.rs::parse_attrval: accepts
  KEY=[V1, V2, ...] (trailing comma optional) alongside the existing
  KEY=V single-value form, expanding a bracket list into N "KEY=V"
  strings at parse time. Widened parse_attrval's return type from
  Result<String, _> to Result<Vec<String>, _>; the four call sites
  (grammar_node.rs, grammar_flow.rs, grammar_infra.rs x2) all already
  `.extend()`ed from a single push, so this was the only call-site
  change needed anywhere in the Rust grammar.
- frob.strata._sync_interface's writer (_render_interface_block) now
  emits the compact form, NAMES_PER_LINE (6) symbols per wrapped line
  purely for readability. The reader (_find_interface_span) recognizes
  BOTH the compact block it now writes and the legacy one-line-per-symbol
  form (backward compat for a file not yet migrated), and ALWAYS writes
  the compact form -- including a one-time reformat of an
  already-correct legacy declaration whose symbol SET already matches
  real, so a single `frob sys sync-interface` run migrates an entire
  repo off the old form with no separate migration script.

Measured: migrating this repo's own design/frob.strata via
`frob sys sync-interface` took it from 5588 lines (pre-T-1198, including
8 lines T-1196 itself added) to 2207 lines -- a ~60% reduction --
confirmed idempotent immediately after (`frob sys sync-interface --check`
reports zero drift).

Disclosed cut: no dedicated Rust unit test was added for
parse_attrval's new bracket-list branch. `cargo test` in this worktree
hit an unrelated, pre-existing environment defect (pyo3-build-config
refusing to build against the worktree's system Python 3.10 while the
crate targets abi3-py311, and separately a broken LD_LIBRARY_PATH for
libpython3.11.so at runtime) -- confirmed this predates my change by
testing on an untouched checkout of the same commit range. Coverage
instead comes from the Python side through the real FFI boundary
end-to-end: tests/unit/strata/test_sync_interface.py's migration test
parses+elaborates+round-trips an `attr interface=[...]` fixture, and
the whole tests/unit/strata/ suite (which exercises design/frob.strata
itself, now fully migrated) passes.

Gates (pre-merge): frob check --only sys --only doclink --only docanchor
(repo-wide) -- 0 errors both before and after design/frob.strata's full
migration. tests/unit/strata/ full suite: all green (including
test_selfconform.py, test_conform_eval_needle.py after `frob sys
sync-interface` registered the new NAMES_PER_LINE symbol). `frob sys
sync-interface --check` reports zero drift post-migration (idempotency
proof).

Merge with main (this update): `git merge main` conflicted on 6 regions
of design/frob.strata -- every conflict was one node's own `interface=`
declaration, this branch's compact bracket-list form against main's
newly-added individual `attr interface=X;` lines for symbols that landed
on main today (T-1471/T-1443/T-1417/T-1394 and others). Resolved
mechanically: parsed both sides' declared symbol sets per node, took the
UNION, and re-rendered each node's block with the same compact-form
renderer (`_render_interface_block`, NAMES_PER_LINE=6, sorted) the
ticket's own code uses -- confirmed by direct comparison afterward that
every symbol main's copy of design/frob.strata declared for every node
is present in this branch's post-merge copy (19/19 nodes, zero missing).
A 7th conflicted region was a single new `// frob:ticket T-1501` comment
line with no branch-side content at that spot; took main's side. The six
sibling-scope conflicts named in the merge brief (src/frob/refactor/**,
tests/test_refactor.py, docs/commands/refactor.md,
docs/design/registry/check-coverage.yaml -- stale pre-T-1201 copies on
this branch) and the four land-owned files (.frob-release.json,
CHANGELOG.md, pyproject.toml, uv.lock) were taken verbatim from main.

The merge also exposed a pre-existing ledger staleness unrelated to
design/frob.strata: this worktree's tickets.md still carried 41 tickets
as active/in-progress blocks that main had already archived (state
transitions this worktree never saw land). The merge driver spliced
tickets.md's own textual conflict cleanly, but a ticket id present as an
active block AND an archive block is a hard DuplicateId load failure,
not a warning -- confirmed each of the 41 stale active copies had a
newer, authoritative block in tickets-archive.md and removed only the
stale active-side duplicates (tickets-archive.md untouched, T-1198's own
block unaffected -- verified it is not among the 41 and was never on
main to begin with).

Post-merge verification: `frob check --only sys` -- 0 errors, 1 warning
(the expected --only scope-note); the strata design loads with no parse
or bind errors. `frob ticket show T-1198` loads cleanly (proves the
DuplicateId fix). All 6 of this ticket's bound evidence node ids plus
the rest of tests/unit/strata/test_sync_interface.py (12/12) pass.
`git diff main --diff-filter=D --stat` is empty -- no file this ticket's
scope touches was dropped relative to main.

### Changed
```
 design/frob.strata                       | 5470 +++++-------------------------
 docs/strata/surface.md                   |  155 +-
 src/frob/strata/_design_load.py          |  105 +-
 src/frob/strata/_multifile.py            |  205 ++
 src/frob/strata/_sync_interface.py       |  191 +-
 strata-core/src/parse/grammar_core.rs    |   44 +-
 strata-core/src/parse/grammar_flow.rs    |    2 +-
 strata-core/src/parse/grammar_infra.rs   |    4 +-
 strata-core/src/parse/grammar_node.rs    |    2 +-
 strata-core/src/parse/lexer.rs           |    4 +-
 tests/unit/strata/test_design_load.py    |   44 +
 tests/unit/strata/test_multifile.py      |  100 +
 tests/unit/strata/test_sync_interface.py |   51 +-
 tickets.md                               |  273 +-
 14 files changed, 1875 insertions(+), 4775 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_legacy_form_migrated_even_with_matching_symbol_set` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_store_block_missing_interface_attr_is_written` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 5 error(s), 6344 warning(s), 782 waived
- error-findings: INV006@src/frob/strata/_multifile.py, PRE001@tickets/T-1198, TEST001@src/frob/strata/_multifile.py, TICK006@tickets.md, WIRE001@tests/unit/strata/test_multifile.py
