---
id: T-4690
title: 'Delete every CLI alias and duplicate name: the four group verbs, fmt, docs/docs-search,
  three spellings of status, whereis'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4687
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_explore.py
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_status.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/_verify.py
- src/frob/_cli_parsers/_shims.py
- src/frob/__main__.py
- src/frob/app/explore_runner.py
- src/frob/app/quality_runner.py
- src/frob/app/design_runner.py
- src/frob/app/status_runner.py
- src/frob/app/fmt_runner.py
- src/frob/app/docs_runner.py
- src/frob/app/doctor_runner.py
- tests/unit/test_cli_shims.py
- tests/unit/test_main_entry.py
- tests/unit/test_cli_group_parity.py
- src/frob/app/app.py
- src/frob/app/_config_external.py
- docs/commands/outline.md
- docs/commands/map.md
- docs/commands/xref.md
- docs/commands/scaffold.md
- docs/commands/exports.md
- changelog.d/T-4690.md
- tests/test_app.py
- src/frob/gates/_sys_provenance.py
- src/frob/strata/_pii.py
- src/frob/worktrees/_disposable_sweep.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/doctor.py
- src/frob/gates/_docptr.py
- src/frob/gates/_fix_engine_scope.py
- src/frob/gates/_prework.py
- src/frob/tickets/_land_squash.py
- src/frob/verify/_quarantine.py
- src/frob/app/ticket_runner/_verify.py
- docs/modules/clean.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ops.py
  reason: T-5092 holds live lease on _ops.py; will re-add once it lands
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/ops_runner.py
  reason: T-5092 holds live lease on _ops.py; will re-add once it lands
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_cli_group_parity.py
  reason: T-4690 deletes the flat docs-search mirror (never dispatchable) that this
    parity test asserted exists; the test itself encodes the pre-T-4690 duplication
    invariant and must be updated to match the ticket's own acceptance criteria
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/app/app.py
  reason: App.__call__ is the single correct interception point for the shared deprecation-shim
    announcement (quality/design/ops groups, outline/map/xref mirrors, verify status/fleet
    status) -- avoids duplicating the sunset check per-runner; _config_external.py's
    _BOOL_FLAGS allowlist had to gain doctor_whereis or the new frob doctor --whereis
    flag silently no-ops (found while implementing T-4690)
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/app/_config_external.py
  reason: App.__call__ is the single correct interception point for the shared deprecation-shim
    announcement (quality/design/ops groups, outline/map/xref mirrors, verify status/fleet
    status) -- avoids duplicating the sunset check per-runner; _config_external.py's
    _BOOL_FLAGS allowlist had to gain doctor_whereis or the new frob doctor --whereis
    flag silently no-ops (found while implementing T-4690)
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/commands/outline.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/commands/map.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/commands/xref.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/commands/scaffold.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/commands/exports.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: changelog.d/T-4690.md
  reason: DOC004/DOC006 require docs/commands/*.md pages naming a removed/deprecated
    verb updated in the same ticket; changelog.d/T-4690.md is the land's changelog
    fragment for the deprecations this ticket introduces
  actor: logan
  at: '2026-09-21'
- op: add
  glob: tests/test_app.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/gates/_sys_provenance.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/strata/_pii.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/worktrees/_disposable_sweep.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/doctor.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/gates/_docptr.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/gates/_fix_engine_scope.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/gates/_prework.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4690 on repo-wide
    drift/DOC/DSL findings accumulated on dev since this worktree branched (none of
    these functions are T-4690''s own edits) -- coordinator directive: fix each finding
    at its root regardless of prior declared scope since the sweep itself is unscoped'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/modules/clean.md
  reason: 'root-cause fix for the DOC002 anchor mismatch: the heading''s inline HTML
    waive-comment is being slugified into the anchor text, producing an unresolvable
    anchor -- moving the frob:waive DOC006 onto its own line below the heading is
    the real fix, not a citation-side workaround'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/modules/clean.md
  reason: 'root-cause fix for the DOC002 anchor mismatch: the heading''s inline HTML
    waive-comment is being slugified into the anchor text, producing an unresolvable
    anchor -- moving the frob:waive DOC006 onto its own line below the heading is
    the real fix, not a citation-side workaround'
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.534.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3416
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3416
- mode: set
  reason: 'DOC006: a planned CLI option must not read as a cli invocation pointer
    until it exists'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3436
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 3436
  new_length: 4480
- mode: set
  reason: 'DOC006: planned options must not read as cli invocation pointers (second
    occurrence)'
  actor: logan
  at: '2026-09-19'
  old_length: 4480
  new_length: 4493
evidence:
- tests/unit/test_cli_shims.py::TestIsPastSunset::test_before_sunset_is_false
- tests/unit/test_cli_shims.py::TestIsPastSunset::test_on_sunset_is_false
- tests/unit/test_cli_shims.py::TestIsPastSunset::test_after_sunset_is_true
- tests/unit/test_cli_shims.py::TestAnnounceShim::test_before_sunset_prints_notice_and_returns
- tests/unit/test_cli_shims.py::TestAnnounceShim::test_after_sunset_exits_nonzero
- tests/unit/test_cli_shims.py::TestAnnounceShim::test_never_writes_to_stdout
- tests/unit/test_cli_shims.py::TestDeprecatedSpellingsTable::test_every_deleted_group_verb_is_covered
- tests/unit/test_cli_shims.py::TestDeprecatedSpellingsTable::test_every_deleted_explore_mirror_is_covered
- tests/unit/test_cli_shims.py::TestDeprecatedSpellingsTable::test_verify_status_and_fleet_status_redirect_to_top_level_status
- tests/unit/test_cli_shims.py::TestSuppressedFromUsageLine::test_deleted_names_absent_from_usage_choices
- tests/unit/test_cli_shims.py::TestSuppressedFromUsageLine::test_explore_survives_in_usage_choices
- tests/unit/test_cli_shims.py::TestPrintWhereis::test_plain_output_names_the_live_executable
- tests/unit/test_cli_shims.py::TestPrintWhereis::test_json_output_is_parseable
- tests/unit/test_cli_shims.py::TestCitationSweep::test_no_markdown_code_fence_recommends_a_deleted_group_verb
- tests/unit/test_cli_group_parity.py::TestExploreGroupParity::test_docs_search_has_no_flat_twin
- tests/unit/test_cli_group_parity.py::TestExploreGroupParity::test_every_explore_leaf_matches_its_flat_twin[xref]
designated_repro_test: null
acceptance:
- text: Given the built argparse tree, when frob --help runs after this ticket, then
    explore SURVIVES in the usage line while its standalone mirrors outline, map,
    xref and docs-search are absent, and quality, design, ops, fmt, docs, whereis
    and the verify status / fleet status spellings are absent
  evidence:
  - tests/unit/test_cli_shims.py::TestSuppressedFromUsageLine::test_deleted_names_absent_from_usage_choices
  - tests/unit/test_cli_shims.py::TestSuppressedFromUsageLine::test_explore_survives_in_usage_choices
- text: Given a deprecated spelling before its sunset date, when it is invoked, then
    it prints the surviving spelling on stderr and exits 0; given the same spelling
    after the sunset date, then it exits non-zero
  evidence:
  - tests/unit/test_cli_shims.py::TestAnnounceShim::test_before_sunset_prints_notice_and_returns
  - tests/unit/test_cli_shims.py::TestAnnounceShim::test_after_sunset_exits_nonzero
- text: Given git grep over .claude/ docs/ scripts/ src/ tests/ for every deleted
    name, when the sweep is re-run at close, then it returns zero hits outside the
    shim definitions themselves; the hits in ~/.claude/refs/frob.md are listed in
    the Done report instead of edited
  evidence:
  - tests/unit/test_cli_shims.py::TestCitationSweep::test_no_markdown_code_fence_recommends_a_deleted_group_verb
- text: Given frob explore map, frob explore outline, frob explore xref and frob explore
    docs-search after this ticket, when each runs, then it works unchanged -- explore
    is the surviving verb and this ticket must not delete or rebuild it; _mirror_subparser
    is removed once it has no callers
  evidence:
  - tests/unit/test_cli_group_parity.py::TestExploreGroupParity::test_docs_search_has_no_flat_twin
  - tests/unit/test_cli_group_parity.py::TestExploreGroupParity::test_every_explore_leaf_matches_its_flat_twin[xref]
acceptance_amendments:
- op: replace
  index: 1
  old_text: Given the built argparse tree, when frob --help runs after this ticket,
    then explore, quality, design, ops, fmt, docs, whereis and the verify status /
    fleet status spellings are absent from the usage line
  new_text: Given the built argparse tree, when frob --help runs after this ticket,
    then explore SURVIVES in the usage line while its standalone mirrors outline,
    map, xref and docs-search are absent, and quality, design, ops, fmt, docs, whereis
    and the verify status / fleet status spellings are absent
  reason: '2026-09-19 coordinator review: explore is the surviving verb, not a deletion
    target; removing the delete-then-rebuild cycle between this ticket and T-4695'
  actor: logan
  at: '2026-09-19'
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4690
branch: t-4690
---
POINTS: 3. Parent story T-4687. blocked_by: none (runs in parallel with T-4689).
This leaf also builds the shared deprecation-shim helper that T-4692, T-4695,
T-4696 and T-4698 all import, which is why those four are blocked on it.

OWNER DECISION: "Delete the duplicates."

AMENDED 2026-09-19 (coordinator review): the earlier version of this ticket
deleted `explore` and had T-4695 rebuild it. That was delete-then-rebuild churn
on the same verb. REVISED: `explore` is the SURVIVING verb and is never deleted.
This leaf deletes its standalone mirrors; T-4695 then moves more leaves under it.

MEASURED 2026-09-19. Four verb GROUPS exist that added names and removed none:
  explore  (T-1238) -> map, outline, xref, docs-search
  quality  (T-1567) -> check, test, dup, arch, bind, cycle, mutate, perf
  design   (T-1568) -> sys, registry, docs, graph, exports
  ops      (T-1569) -> release, natives, doctor, clean, fleet, deploy,
                       scaffold, gitlog, stats, process
`_cli_parsers/_explore.py::_mirror_subparser` proves the duplication literally:
it writes the FLAT parser object into the group's `choices` dict, so
`frob explore xref` and `frob xref` are the same ArgumentParser instance.
None of these four group verbs has ever been recorded in a kind=cli row.

KEEP: `explore`. It has 95 citations across .claude/ docs/ scripts/ src/ tests/
("frob show" has 0), and T-4695 folds the rest of the read-only surface under
it. Keeping it here is what makes T-4695 an additive move rather than a rebuild.

DELETE, each with a one-minor-version shim:
  - the standalone top-level mirrors of explore's four existing leaves:
    `outline`, `map`, `xref`, `docs-search`. The surviving spelling for each is
    `frob explore <leaf>`. `xref` has 16 recorded kind=cli invocations -- it is
    the one mirror with a live consumer, so its shim must actually work, not
    merely exist.
  - the three remaining group verbs `quality`, `design`, `ops`
  - `fmt` -> `format` (already marked DEPRECATED, sunset 2026-12-01; finish it)
  - `docs` vs `docs-search`: keep `docs-search` (under `explore`) as the search
    surface; `docs`'s docstring-extraction mode survives under that one name
  - `status` vs `verify status` vs `fleet status`: three spellings, one concept.
    Keep top-level `status`; `verify status` and `fleet status` become shims.
  - `whereis` folded into `doctor` (a whereis option on doctor (planned) or a section of
    plain `frob doctor` output). `whereis` (T-4299) answers "which interpreter
    is this frob" -- that is a doctor question.

ONCE `_mirror_subparser` HAS NO CALLERS, DELETE IT. It exists only to make one
parser object answer to two names, which is the duplication this story removes.

BUILD, once, for the whole story: a single shim helper (suggested home
src/frob/_cli_parsers/_shims.py) that registers a deprecated name, prints the
surviving spelling to stderr on every use, and exits non-zero once the sunset
date has passed. It MUST be expressed through the existing frob:deprecated
machinery (src/frob/gates/_debt_deprecated.py, _deprecated_baseline.py,
src/frob/app/deprecated_runner.py) and follow the `fmt` precedent in
src/frob/app/fmt_runner.py. Do NOT invent a second mechanism -- a second
deprecation path is exactly the duplication this story is deleting.

CITATION SWEEP (acceptance evidence): `git grep` every deleted name across
.claude/, docs/, scripts/, src/, tests/ and update each citation to the
surviving spelling. ~/.claude/refs/frob.md is the OWNER'S file and is OUT OF
SCOPE -- list the edits it needs in the Done report, do not touch it.

FILES (declared scope):
  src/frob/_cli_parsers/_explore.py, _quality.py, _design.py, _ops.py,
  _status.py, _core.py, _misc.py, _reporting.py, _verify.py, _shims.py (new)
  src/frob/__main__.py
  src/frob/app/explore_runner.py, quality_runner.py, design_runner.py,
  ops_runner.py, status_runner.py, fmt_runner.py, docs_runner.py,
  doctor_runner.py
  tests/unit/test_cli_shims.py (new), tests/unit/test_main_entry.py
NOTE: _core.py, _misc.py, _reporting.py, _explore.py and __main__.py are
contended with T-4692 and T-4695; that is why those two are blocked on this
ticket rather than declared disjoint. A frob scope is a write lease and cannot
be shared.

TITLE DRIFT: this ticket's title still says "the four group verbs". After this
amendment it is three group verbs plus four standalone mirrors. `frob ticket`
has no title setter; this paragraph is the correction of record.

## Reopen log
- 2026-09-21: closed-but-unlanded: a refused drain wrote state=done with land_commit null and no code on dev; reopen to land for real
