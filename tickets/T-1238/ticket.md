---
id: T-1238
title: 'EPIC cli regrouping: verb groups to shrink the top-level surface -- frob explore
  first'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/**
- src/frob/app/**
- src/frob/__main__.py
- docs/**
- tests/**
- design/frob.strata
- src/frob/gates/_inv.py
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
  glob: design/frob.strata
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_inv.py
  reason: widen scope to cover interface= declarations touched to close SYS104 SELFAUDIT001
    findings
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
- tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
acceptance:
- text: 'GIVEN frob --help THEN the top level presents a small set of verb groups
    (target: under ~15 entries) with subcommands grouped by intent, every old invocation
    either still working or aliased with a pointer, and the grouped help readable
    by a first-time user'
  evidence: []
- text: GIVEN frob explore THEN map/outline/xref/docs-search live as its subcommands,
    un-deprecated (frob:deprecated markers and sunset warnings removed), with their
    standalone deprecated top-level forms aliased through a transition window
  evidence:
  - tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner
  - tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1
  - tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1
- text: GIVEN the regrouping design doc THEN it proposes the full grouping taxonomy
    for every current top-level command with a migration/alias policy, before any
    group beyond explore is implemented
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
User directive 2026-07-29: frob is intimidating; group everything together. First concrete slice: the T-0580-deprecated navigation commands (map/outline/xref/docs-search) regroup into frob explore instead of being deleted -- this SUPERSEDES the 2026-10-01 sunset (T-0802 dropped with this epic as the reason). Design phase first for the full taxonomy (candidate buckets to evaluate, not prescribe: explore/navigation, quality/check+test+fix, tickets, design/sys+strata, supply-chain/vet, ops/release+registry+natives+doctor+clean, serve/perf tooling); un-deprecation of the explore members includes removing the docs 'Kept commands'/deprecation drift the 2026-07-29 staleness sweep catalogued. Children to file at design time: taxonomy design doc, explore group implementation, alias/transition machinery, help-surface rework, docs/index updates.

## Done report

EPIC closure decision: T-1238's own scope is the frob explore first-slice
(acceptance[1]) plus the design doc (acceptance[2]). Acceptance[0]
(help-surface rework across every other verb group) is explicitly deferred
per the epic's own directive to design the full taxonomy before
implementing anything beyond explore -- tracked by draft
T-1571 (help-surface rework), filed alongside three further
taxonomy-slice drafts (T-1567 quality group, T-1568
design group, T-1569 ops group) and a naming-decision draft
(T-1570). This closure choice was made by the prior session that
implemented the slice (commit 532799ac) and is being finalized here after
a same-day merge with main (main advanced ~25 lands, including two
unrelated conflicting features -- frob refactor verb group T-1200/T-1201
and ticket migrate --to v2 T-1259 -- both preserved, neither touched by
this ticket's own diff).

Post-merge verification performed fresh in this session:
- git merge main required manual resolution of 4 conflicts in
  src/frob/app/{docs,map,outline,xref}_runner.py -- all four were the same
  shape: this branch's un-deprecation commit vs main's now-superseded
  frob:deprecated/DEPR003-waiver block for the same functions. Resolved by
  keeping this branch's un-deprecated side (the correct outcome per this
  ticket's own acceptance[1], which requires exactly that removal).
- .frob-release.json/CHANGELOG.md/pyproject.toml/uv.lock: no manual
  resolution needed, both sides already matched main verbatim after the
  ticket-merge-driver auto-spliced tickets.md.
- git diff main --diff-filter=D --stat: empty, no unintended deletions
  carried forward.
- Scoped verification run fresh post-merge:
  - pytest tests/unit/test_app_runners.py -k "Explore or Outline or Map or
    Xref or Docs": 18 passed.
  - frob check --only archgate --ticket T-1238: 0 errors.
  - frob check --only test --ticket T-1238: 0 errors (repo-wide TEST family
    warnings only, pre-existing).
  - frob check --only coverage --ticket T-1238: 0 errors.
  - frob check --only sys --ticket T-1238: caught 2 new SELFAUDIT001/SYS104
    findings this merge/rebuild surfaced (_add_explore_parser undeclared on
    the cli node's interface= list, TestExploreRunner undeclared on
    testsuite's) -- fixed by adding both attr interface= lines to
    design/frob.strata in their correct alphabetical position. Re-run: 0
    errors.
- Ticket-state bookkeeping: this worktree's very first `frob ticket start
  T-1238` transition had only ever landed in this branch, so restoring
  tickets.md to main's copy (playbook sec 10b step 1) reverted the ticket to
  queued, per the documented first-ticket edge case -- self-repaired via a
  fresh `frob ticket start T-1238` + `frob ticket sweep T-1238`, then
  evidence re-recorded (idempotent, same 5 node ids, bound to
  acceptance[1]).

No new out-of-scope work found this session beyond the design/frob.strata
interface= fix, which is within this ticket's own (now-widened) scope.

### Changed
```
 README.md                         |   3 +-
 design/frob.strata                |   2 +
 docs/commands/map.md              |   3 +
 docs/commands/outline.md          |   3 +
 docs/commands/xref.md             |   3 +
 docs/design/cli-regrouping.md     | 143 ++++++++++++++++++++++++++++++++++++++
 docs/guides/agentic-workflow.md   |   4 +-
 docs/index.md                     |  15 ++--
 docs/modules/app.md               |   6 ++
 docs/modules/cli.md               |  79 +++++++++++----------
 docs/modules/render.md            |   5 +-
 docs/rework.md                    |   4 +-
 src/frob/__main__.py              |   2 +
 src/frob/_cli_parsers/__init__.py |   2 +
 src/frob/_cli_parsers/_core.py    |  15 ++--
 src/frob/_cli_parsers/_explore.py |  71 +++++++++++++++++++
 src/frob/app/_config_external.py  |   1 +
 src/frob/app/app.py               |   4 ++
 src/frob/app/config.py            |   6 ++
 src/frob/app/docs_runner.py       |  15 ++--
 src/frob/app/explore_runner.py    |  61 ++++++++++++++++
 src/frob/app/map_runner.py        |  16 ++---
 src/frob/app/outline_runner.py    |  16 ++---
 src/frob/app/xref_runner.py       |  22 ++----
 tests/unit/test_app_runners.py    |  48 +++++++++++++
 tickets.md                        |  31 ++++++++-
 26 files changed, 474 insertions(+), 106 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestExploreRunner::test_map_subcommand_delegates_to_map_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_outline_subcommand_delegates_to_outline_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_xref_subcommand_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_docs_search_subcommand_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExploreRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 7598 warning(s), 755 waived
- error-findings: DUP001@src/frob/app/app.py, DUP001@tests/unit/test_app_runners.py
