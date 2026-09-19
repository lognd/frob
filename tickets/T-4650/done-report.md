## Done report

Ticket: T-4650 "Registry-file class: append-shared, not whole-file leases"
Worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-aefc4511 (branch t-draft-aefc4511)
Final commit: b71f6a85f

UPDATE (land-repair #5, second land refusal): the 16:02 land was
refused for two reasons. Reason 1 (T-3259's stale gates.md lease) is
the coordinator's own fix, applied to ROOT, not this worktree. Reason
2 -- "evidence no longer resolves post-merge:
tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff::test_deleted_line_is_not_additive"
-- is fixed here: HEAD was a no-op `wip: pre-land snapshot` commit
(only a CHANGELOG.md line, discarded since dev's CHANGELOG.md wins on
merge anyway) so it was `git reset --soft`'d off, then `git merge dev
--no-edit` was run (5 ticket.md files merged clean, no conflicts on
any of the take-dev's-side paths). The stale evidence id
`TestAdditiveOnlyDiff::test_deleted_line_is_not_additive` was a
leftover duplicate of two ids that already exist correctly in the
evidence list under the post-split class names
(`TestIsAdditiveDiffText::test_deleted_line_is_not_additive` and
`TestRegistryFileDiffIsAdditive::test_deleted_line_is_not_additive`,
both already bound) -- the ticket's own `evidence_changes` audit trail
already recorded the rename reason but had never actually filled in
the replacement node id. Rebound via
`frob ticket evidence T-4650 --replace
"tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff.test_deleted_line_is_not_additive"
"tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive.test_deleted_line_is_not_additive"
--reason "..."` and committed (b71f6a85f). All 18 evidence node ids
now resolve; ran the full test_tickets_registry_files.py suite
post-merge to confirm (SUITE-RESULT: exitstatus=0 collected=18
failed=0).

gates.md lease check: `.git/frob-leases/*.json` grep for "gates.md"
under ROOT now shows only T-4650.json holding it (T-3259 was
already dropped by the coordinator before this pass started) -- no
other in-progress ticket holds a conflicting lease on any file this
ticket touches.

UPDATE (post-first-READY): T-4116's lease released while polling, so
docs/modules/gates.md was scope-added and dogfooded with a real doc
edit (CROSSTICKET001 section update, additive-only). T-4221 (design/
frob.strata, capability-via-ratchet.lock.json) and T-4112 (docs/design/
registry/check-coverage.yaml) never released across three consecutive
45/45/30-minute polls, so per the coordinator's later instruction the
SELFAUDIT001 gap was closed differently: the `git diff` subprocess call
was moved OUT of the new frob.tickets._registry_files module (which has
no via-declared exec capability of its own and could not get one while
design/frob.strata stayed leased) and INTO frob.tickets._land as
_registry_file_diff_is_additive, reusing frob.gitio.run_argv -- the
exact capability _branch_changed_files (immediately above it in the
same file) already exercises and already has a via grant for.
frob.tickets._registry_files now only does a pure text scan
(is_additive_diff_text), no subprocess at all. `frob check --only sys`
now reports ZERO SELFAUDIT001 findings against any touched file; the
one SELFAUDIT001 line left in the run's output is SYS111's pre-existing
testsuite-glob ceiling note (self-described as "pending auto-accept",
unattributable to this diff -- see "Gates" section below).
docs/design/registry/check-coverage.yaml is left unscoped (still leased
by T-4112); its row is deferred to T-4605 per the coordinator.

WHAT changed, per file
-----------------------
- src/frob/tickets/_registry_files.py (NEW): the single home for the
  registry-file class.
    - DEFAULT_REGISTRY_FILES: the four paths named in the ticket
      (design/frob.strata, docs/design/registry/capability-via-
      ratchet.lock.json, docs/modules/gates.md, docs/design/registry/
      check-coverage.yaml).
    - registry_files(root): reads [tickets].registry_files from
      frob.toml, falling back to DEFAULT_REGISTRY_FILES on missing
      root/file/key or a malformed value -- mirrors
      frob.tickets._doable._default_milestone's own fail-open shape.
    - is_registry_file(path, root): membership test.
    - additive_only_diff(worktree, base_ref, path): runs
      `git diff <base_ref>...HEAD -- <path>` and returns True only when
      no line in the diff starts with a single `-` (never `---`). Fails
      closed (False) on any subprocess/OSError.

- src/frob/tickets/_models.py: scope_matches now treats every path in
  DEFAULT_REGISTRY_FILES as always implicitly in scope, the same
  LEDGER_PATH-always-in-scope shape it already uses for tickets.md
  (acceptance a). Fixed default set (not root-configured) because this
  function has ~30 existing call sites with no root parameter to read a
  per-repo override from.

- src/frob/tickets/_land.py: new _registry_leakage_exempt_paths(worktree,
  base_ref, changed_paths) -- the subset of changed_paths that is BOTH a
  configured registry file (registry_files(worktree), so a per-repo
  override IS honored here) AND additive_only_diff for it is True. Wired
  into both _check_cross_ticket_leakage's and
  _cross_ticket_leakage_findings's `relevant` set computation, alongside
  the existing _machinery_owned_leakage_exempt_paths() subtraction
  (acceptances b and c: additive-only diffs are exempted, destructive
  diffs are not, since a path only leaves `relevant` when the additive
  check actually passes).

- frob.toml: added [tickets].registry_files explicitly (matching the
  in-code default) -- this repo is the first to declare the key.

- docs/modules/tickets.md: new "Registry files (append-shared,
  T-4650)" section documenting the mechanism and all three
  effects, anchored at
  #registry-files-append-shared-t-draft-a62505d4 (every frob:doc
  directive in the new code points here).

- tests/test_tickets_registry_files.py (NEW): 14 tests, real git-repo
  fixtures for the diff-shape tests, covering registry_files/
  is_registry_file/additive_only_diff, scope_matches's implicit-scope
  rule, and _registry_leakage_exempt_paths directly.

WHAT changed, per file (post-update additions)
------------------------------------------------
- src/frob/tickets/_registry_files.py: `additive_only_diff` (subprocess)
  replaced by `is_additive_diff_text(diff_text: str) -> bool` (pure,
  no exec capability at all).
- src/frob/tickets/_land.py: new `_registry_file_diff_is_additive
  (worktree, base_ref, path)` runs `git diff <base_ref>...HEAD -- <path>`
  via `frob.gitio.run_argv` (same capability `_branch_changed_files`
  already exercises) and hands the text to `is_additive_diff_text`;
  `_registry_leakage_exempt_paths` now calls this instead of the old
  `additive_only_diff`.
- docs/modules/gates.md: CROSSTICKET001's own section documents the new
  `_registry_leakage_exempt_paths` subtraction alongside the existing
  machinery-owned one (dogfooding the mechanism: this is an
  additive-only edit to a registry file, committed while
  docs/modules/gates.md was in scope after T-4116 released).
- tests/test_tickets_registry_files.py: `TestAdditiveOnlyDiff` split
  into `TestIsAdditiveDiffText` (pure, string-fixture tests, no git
  needed) and `TestRegistryFileDiffIsAdditive` (real-git-repo tests
  against the new `_land` function) -- 18 tests total, all passing.

HOW each acceptance criterion is proven
----------------------------------------
(a) "no declared scope over gates.md ... scope_lease_conflict never
    refuses, no --add required" -- proven at the scope_matches layer
    (the mechanism this repo already uses for the identical LEDGER_PATH
    guarantee: an implicitly-in-scope path is never passed to
    scope_lease_conflict via --add in normal use, so the lease-conflict
    path is never reached):
      TestScopeMatchesRegistryImplicit.test_registry_file_matches_with_empty_scope
      TestScopeMatchesRegistryImplicit.test_registry_file_matches_with_unrelated_scope

(b) "two siblings both appending distinct lines ... second lands,
    CrossTicketLeakage does not refuse":
      TestRegistryLeakageExemptPaths.test_additive_registry_change_is_exempt

(c) "branch deletes/rewrites a line it did not add ... still refuses":
      TestRegistryLeakageExemptPaths.test_destructive_registry_change_is_not_exempt

All 18 test node ids are bound as evidence on T-4650 (the
first three below bound to acceptance indices 1/2/3 respectively via
`frob ticket evidence --accepts`; the two stale `TestAdditiveOnlyDiff`
ids from the pre-update evidence set were removed via `--remove
--reason` once that class was split/renamed).

Test node ids (all pass, `PYTHONPATH=<worktree>/src python -m pytest
tests/test_tickets_registry_files.py -q` -> SUITE-RESULT:
exitstatus=0 collected=18 failed=0):
  tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_root_returns_default
  tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_frob_toml_returns_default
  tests/test_tickets_registry_files.py::TestRegistryFiles::test_configured_override_replaces_default
  tests/test_tickets_registry_files.py::TestRegistryFiles::test_malformed_value_falls_back_to_default
  tests/test_tickets_registry_files.py::TestRegistryFiles::test_is_registry_file_membership
  tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_pure_append_is_additive
  tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_deleted_line_is_not_additive
  tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_file_header_dashes_are_not_removed_lines
  tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_empty_diff_is_additive
  tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_pure_append_is_additive
  tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_deleted_line_is_not_additive
  tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_bad_ref_fails_closed
  tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_empty_scope
  tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_unrelated_scope
  tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_non_registry_file_still_requires_declared_scope
  tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_additive_registry_change_is_exempt
  tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_destructive_registry_change_is_not_exempt
  tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_non_registry_path_is_never_exempt

Also re-ran the pre-existing suite to confirm no regression:
  tests/unit/test_cross_ticket_leakage_gate.py + tests/test_tickets.py
  -k "ScopeMatch or CrossTicket" -> 14 passed, 0 failed.

Commits (chronological)
------------------------
147c6b191  feat(tickets): add append-shared registry-file class (T-4650)
67f1c9517  chore(tickets): bind frob:ticket/frob:tests/frob:doc on registry-file symbols
de6977616  chore(tickets): bind frob:doc on DEFAULT_REGISTRY_FILES (COV001)
4b8b3e539..014432abe  chore(tickets): record evidence for T-4650 (x4)
968fbfa13  Merge branch 'dev' into t-draft-aefc4511 (T-4116 released; picked up T-4508/T-4524/T-4562/... lands)
b12fec4af  chore(tickets): scope T-4650 (+docs/modules/gates.md)
ab0dc0bdf  docs(gates): document the registry-file CrossTicketLeakage exemption
1f66610d0  fix(tickets): move registry-file git diff spawn into _land.py
f2b2072f0..0a56682a4  chore(tickets): record evidence for T-4650 (x4: 2 removes of stale TestAdditiveOnlyDiff ids, 1 add of the 7 new/renamed ids)

Gates (--only, --files, --base dev, NOT a bare/--ticket check) -- FINAL
--------------------------------------------------------------------------
- ruff check / ruff format --check: clean on all touched source/test
  files (src/frob/tickets/_registry_files.py, _models.py, _land.py,
  tests/test_tickets_registry_files.py).
- ty check src/frob/tickets/{_registry_files,_models,_land}.py: clean.
- frob check --only arch --files <touched> --base dev: `pass frob-arch,
  19 warnings (36 waived), 544 suggestions` -- 0 ARCH001/LARGE001
  attributable to this diff; the listed warnings are pre-existing
  repo-wide pattern-recommendation noise (Factory-pattern suggestions
  on classes constructed in many files, none of them mine).
- frob check --only coverage --files <touched> --base dev: `FAIL
  gate:COV 9 errors, 118 warnings, 0 unresolved, 280 waived` -- ZERO of
  the 9 errors are on a file this ticket touches (checked by grep on
  each touched path). The only lines that DO mention
  src/frob/tickets/_land.py are pre-existing COV007 findings, already
  WAIVED under this repo's own T-1636 precedent -- including the two
  new private helpers this ticket added
  (_registry_file_diff_is_additive, _registry_leakage_exempt_paths),
  which fall under the exact same waiver class as every other private
  _land.py helper (`[waived: T-1636: docs/design/ledger-v2.md's...]`).
- frob check --only sys --files <touched> --base dev: `FAIL
  gate:SELFAUDIT 1 error` -- and that ONE finding is:
  "SELFAUDIT001: self-audit family SYS111 node=testsuite: fs.write
  testsuite-glob via-list on testsuite grew to 541 site(s) -- pending
  auto-accept: only a land's own composed-tree check run may write
  docs/design/registry/capability-via-ratchet.lock.json for this
  glob-form pair; a bare check outside a land never writes it
  (T-4563)". This is SYS111's own auto-accept ceiling bump for the
  TESTSUITE glob-form (i.e. "how many test files exist total"), not a
  capability declaration on anything this diff wrote -- it is
  attributed to `design:1` (the strata file as a whole), pre-existing,
  and self-describes as "pending auto-accept" resolved by a LAND's own
  composed-tree run, not by a bare `frob check`. It is NOT one of the
  two SELFAUDIT001 exec findings from the first READY -- those are
  GONE: the `git diff` subprocess call was moved into
  frob.tickets._land's `_registry_file_diff_is_additive`, reusing
  frob.gitio.run_argv, the same already-`via`-declared capability
  `_branch_changed_files` exercises immediately above it in the same
  file. Zero SELFAUDIT001 findings are attributable to
  src/frob/tickets/_registry_files.py, _models.py, or _land.py.
  gate:DSL's one pre-existing error (tests/test_app.py:387, a stray
  `# noqa: E501` inside a frob: directive) is unrelated to this diff
  (not one of my files) and was present before this ticket started.

Registry files touched this round
------------------------------------
- docs/modules/gates.md: T-4116's lease released mid-poll; scope-added
  and dogfooded with a real, additive-only edit (the CROSSTICKET001
  section update above) while still in scope.
- design/frob.strata, docs/design/registry/capability-via-ratchet.lock.json:
  T-4221's lease never released across three consecutive polls (45 +
  45 + 30 minutes). Per the coordinator's final instruction, the need
  for a `via` entry there was removed entirely rather than waited out
  further: the exec capability moved to frob.tickets._land, which
  already carries the grant. Nothing in this ticket's diff needs a new
  `via` entry or ratchet bump anywhere.
- docs/design/registry/check-coverage.yaml: still leased (T-4112) at
  the time of this report; left unscoped and untouched. Its
  check-coverage row (if any is needed for the new symbols) is
  deferred to T-4605 per the coordinator's instruction.

Filed: none.

## Pre-READY checks (land-repair #5, re-run post-merge on b71f6a85f)

`frob check --only sys --files docs/modules/gates.md --files docs/modules/tickets.md --files frob.toml --files src/frob/tickets/_land.py --files src/frob/tickets/_models.py --files src/frob/tickets/_registry_files.py --files tests/test_tickets_registry_files.py --base dev`:
  FAIL  gate:DRIFT   6 errors, 0 warnings, 0 unresolved, 5 waived  (unattributable: run_deferred_post_land_sweep/load_invariants/_done_transition_structural_guard/add_cmd_evidence -- none are my touched files)
  FAIL  gate:DSL     1 error   (tests/test_app.py:387, pre-existing, not my file)
  FAIL  gate:SELFAUDIT  1 error  (SYS111 testsuite-glob ceiling note on design:1, self-described "pending auto-accept", not an exec/via finding on any touched file)
  -> ZERO SELFAUDIT001/DRIFT findings attributable to _registry_files.py, _models.py, _land.py, gates.md, tickets.md, frob.toml, or the test file.

`frob check --only arch --files <same 7 files> --base dev`:
  pass  frob-arch   19 warnings (36 waived), 546 suggestions  -> 0 ARCH001/LARGE001 anywhere in the run.

`frob check --only coverage --files <same 7 files> --base dev`:
  FAIL  gate:COV    9 errors, 119 warnings, 0 unresolved, 280 waived  -> all 9 unwaived errors are on files this ticket does not touch (_cli_parsers/_check.py, graph/dsl.py, strata/_effects.py, strata/_unity_asmdef.py, gates/_waive.py, _cli_parsers/_core.py); every COV hit that does name _land.py or _models.py is already [waived] under the repo's existing T-1636/T-1024 precedent. No COV findings at all against _registry_files.py.
  FAIL  gate:DRIFT/DSL/TODO also reported in this run's rollup, same pre-existing unattributable findings as the sys check above.

`ruff check docs/modules/gates.md docs/modules/tickets.md frob.toml src/frob/tickets/_land.py src/frob/tickets/_models.py src/frob/tickets/_registry_files.py tests/test_tickets_registry_files.py`:
  All checks passed!

`ruff format --check src/frob/tickets/_land.py src/frob/tickets/_models.py src/frob/tickets/_registry_files.py tests/test_tickets_registry_files.py`:
  4 files already formatted

`ty check src/frob/tickets/_land.py src/frob/tickets/_models.py src/frob/tickets/_registry_files.py tests/test_tickets_registry_files.py`:
  All checks passed!

`PYTHONPATH=<worktree>/src python -m pytest tests/test_tickets_registry_files.py -p no:cacheprovider -q`:
  SUITE-RESULT: exitstatus=0 collected=18 failed=0

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  65 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-3943.md                              |   2 +
 changelog.d/T-3961.md                              |   2 +
 changelog.d/T-4111.md                              |   2 +
 changelog.d/T-4116.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
 changelog.d/T-4221.md                              |   2 +
 changelog.d/T-4230.md                              |   2 +
 changelog.d/T-4413.md                              |   2 +
 changelog.d/T-4414.md                              |   2 +
 changelog.d/T-4415.md                              |   2 +
 changelog.d/T-4491.md                              |   2 +
 changelog.d/T-4492.md                              |   2 +
 changelog.d/T-4493.md                              |   2 +
 changelog.d/T-4494.md                              |   2 +
 changelog.d/T-4495.md                              |   2 +
 changelog.d/T-4496.md                              |   2 +
 changelog.d/T-4498.md                              |   2 +
 changelog.d/T-4501.md                              |   2 +
 changelog.d/T-4502.md                              |   2 +
 changelog.d/T-4503.md                              |   2 +
 changelog.d/T-4507.md                              |   2 +
 changelog.d/T-4508.md                              |   2 +
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
 changelog.d/T-4524.md                              |   2 +
 changelog.d/T-4531.md                              |   2 +
 changelog.d/T-4532.md                              |   2 +
 changelog.d/T-4535.md                              |   2 +
 changelog.d/T-4536.md                              |   2 +
 changelog.d/T-4540.md                              |   2 +
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4554.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 changelog.d/T-4556.md                              |   2 +
 changelog.d/T-4562.md                              |   2 +
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4588.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 changelog.d/T-4633.md                              |   2 +
 changelog.d/T-4642.md                              |   2 +
 changelog.d/T-4649.md                              |   2 +
 design/frob.strata                                 | 167 ++--
 docs/commands/check.md                             |  88 +-
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  87 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/extending/comment-dsl-directives.md    |  13 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/guides/unity.md                               |  83 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |  95 +++
 docs/modules/gate-time-stable-invariant.md         |  74 ++
 docs/modules/gates.md                              | 165 +++-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  37 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 ++++-
 docs/modules/tickets.md                            |  70 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 frob.toml                                          |  18 +
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/__init__.py                  |   2 +
 src/frob/_cli_parsers/_check.py                    | 295 ++++++-
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 +++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       | 154 +++-
 src/frob/app/config.py                             |  92 ++-
 src/frob/app/ticket_runner/__init__.py             | 125 ++-
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 ++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 +++++-
 src/frob/check/__init__.py                         | 244 +++---
 src/frob/check/_python.py                          | 152 ++--
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 +++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 +++++
 src/frob/excludes.py                               |  83 +-
 src/frob/gates/__init__.py                         | 263 +++---
 src/frob/gates/_claim_lint.py                      | 202 +++++
 src/frob/gates/_coverage.py                        | 203 ++++-
 src/frob/gates/_fix_engine.py                      |  94 ++-
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 +++++++
 src/frob/gates/_inv.py                             | 359 +++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 +++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 185 ++++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 780 ++++++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 ++++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 ++++++++
 src/frob/testing/_dotnet_runner.py                 | 251 ++++++
 src/frob/testing/_runners.py                       |  10 +
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/testing/_unity_batchmode.py               | 298 +++++++
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 198 ++++-
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   |  49 +-
 src/frob/tickets/_leases.py                        | 552 +++++++++----
 src/frob/tickets/_models.py                        |  66 +-
 src/frob/tickets/_registry_files.py                | 145 ++++
 src/frob/tickets/_setters.py                       | 113 ++-
 src/frob/tickets/_store.py                         | 120 ++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 +++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 +++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 +
 .../python_control/duplicate.py                    |  29 +
 tests/fixtures/dsl_todo_notes/sample.c             |   3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |   3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |   3 +
 tests/fixtures/dsl_todo_notes/sample.java          |   3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |   3 +
 tests/fixtures/dsl_todo_notes/sample.py            |   9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |   3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |   3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |   3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 tests/fixtures/lang/csharp/directives.cs           |  44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 .../lang/csharp/tests/malformed_results.xml        |   5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |  15 +
 .../lang/csharp/tests/sample_unity_results.xml     |   9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 .../Assets/Editor/Editor.asmdef                    |   6 +
 .../Assets/Editor/Editor.asmdef.meta               |   2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |   2 +
 .../Assets/Runtime/Runtime.asmdef                  |   6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |   2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |   6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |   2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |   6 +
 .../Assets/Tests/Tests.asmdef.meta                 |   2 +
 .../unity_sample_asmdef/Packages/manifest.json     |   3 +
 .../ProjectSettings/ProjectVersion.txt             |   2 +
 tests/gates_suite/test_claim_lint.py               | 163 ++++
 tests/gates_suite/test_coverage.py                 | 132 ++-
 tests/gates_suite/test_fix_engine.py               | 123 +++
 tests/gates_suite/test_guard_closure.py            | 228 ++++++
 tests/gates_suite/test_invariant.py                | 116 +++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_docenum_gate.py                         |  41 +
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 ++
 tests/test_lang.py                                 |  90 +++
 tests/test_lang_conformance_gate.py                |  81 +-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 +++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++--
 tests/test_tickets_migration.py                    | 121 +--
 tests/test_tickets_parent.py                       | 208 +++++
 tests/test_tickets_registry_files.py               | 206 +++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/unit/graph/test_dsl.py                       | 164 +++-
 tests/unit/graph/test_dsl_invariant_property.py    |  69 ++
 tests/unit/lang/test_csharp_directives.py          | 115 +++
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 +++++++++++
 tests/unit/strata/test_effects.py                  |  44 +
 tests/unit/strata/test_selfconform.py              | 460 ++++++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 +--
 tests/unit/test_check_scoped_files.py              | 566 +++++++++++++
 tests/unit/test_check_skip_flag.py                 | 192 +++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 +++++
 tests/unit/test_cli_group_parity.py                | 220 +++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 116 +++
 tests/unit/test_done_report_check_scope.py         | 177 ++++
 tests/unit/test_dotnet_runner.py                   | 194 +++++
 tests/unit/test_land_default_queue.py              | 128 +++
 tests/unit/test_land_in_progress_window.py         | 351 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 +++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 +++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 +++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++
 tests/unit/test_ticket_cli_surface.py              | 182 +++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 +++++
 tests/unit/test_xref.py                            |  40 +
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  17 +-
 tickets/T-2889/ticket.md                           |  23 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 +++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  17 +-
 tickets/T-3053/ticket.md                           |  16 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 +++++
 tickets/T-3232/ticket.md                           |  88 +-
 tickets/T-3233/done-report.md                      | 606 ++++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  24 +-
 tickets/T-3262/ticket.md                           |  17 +-
 tickets/T-3270/ticket.md                           |  17 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3335/ticket.md                           |  17 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  34 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3612/done-report.md                      | 221 +++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 ++++-
 tickets/T-3614/ticket.md                           | 111 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3714/ticket.md                           |  17 +-
 tickets/T-3716/ticket.md                           |  17 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  27 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3856/done-report.md                      | 247 ++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  17 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3882/ticket.md                           |  17 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3904/ticket.md                           |  17 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3943/done-report.md                      | 626 +++++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 ++++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-3997/ticket.md                           |  25 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  11 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 726 +++++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/done-report.md                      | 707 ++++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 +++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/done-report.md                      | 706 ++++++++++++++++
 tickets/T-4221/ticket.md                           |  92 ++-
 tickets/T-4230/done-report.md                      | 723 +++++++++++++++++
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4392/ticket.md                           |  11 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           | 242 +++++-
 tickets/T-4420/ticket.md                           | 382 ++++++++-
 tickets/T-4421/ticket.md                           | 483 ++++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4447/ticket.md                           |  11 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 ++++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 +
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 ++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 ++++++++++++++
 tickets/T-4503/ticket.md                           |  94 +++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/done-report.md                      | 793 ++++++++++++++++++
 tickets/T-4507/ticket.md                           |  57 ++
 tickets/T-4508/done-report.md                      | 689 ++++++++++++++++
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  48 ++
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 ++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 ++++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 +++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 +++++
 tickets/T-4517/ticket.md                           |  94 +++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/ticket.md                           |  67 ++
 tickets/T-4520/done-report.md                      | 163 ++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 ++++++
 tickets/T-4521/ticket.md                           | 125 +++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/done-report.md                      | 209 +++++
 tickets/T-4524/ticket.md                           |  52 ++
 tickets/T-4526/ticket.md                           |  45 ++
 tickets/T-4529/ticket.md                           |  76 ++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 +++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 +
 tickets/T-4534/ticket.md                           |  69 ++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 ++
 tickets/T-4536/ticket.md                           | 128 +++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 +++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 ++
 tickets/T-4547/done-report.md                      | 137 ++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 +++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 ++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 +++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 +++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 ++++++++++++++
 tickets/T-4556/ticket.md                           |  46 ++
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 +
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 +++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 +++++++++++++
 tickets/T-4563/ticket.md                           |  47 ++
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 +
 tickets/T-4572/ticket.md                           |  66 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  52 ++
 tickets/T-4579/done-report.md                      | 522 ++++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 ++
 tickets/T-4581/ticket.md                           |  47 ++
 tickets/T-4582/done-report.md                      | 551 +++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 ++++++++++++++
 tickets/T-4583/ticket.md                           |  87 ++
 tickets/T-4588/done-report.md                      | 715 +++++++++++++++++
 tickets/T-4588/ticket.md                           |  67 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 +++++++++++++++
 tickets/T-4596/ticket.md                           |  43 +
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  29 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 +
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 ++++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 ++
 tickets/T-4608/ticket.md                           |  41 +
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 116 +++
 tickets/T-4615/ticket.md                           | 105 +++
 tickets/T-4616/ticket.md                           |  43 +
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  52 ++
 tickets/T-4619/ticket.md                           |  64 ++
 tickets/T-4620/ticket.md                           |  52 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  64 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 +
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  52 ++
 tickets/T-4628/ticket.md                           |  53 ++
 tickets/T-4629/ticket.md                           |  46 ++
 tickets/T-4630/ticket.md                           |  54 ++
 tickets/T-4631/ticket.md                           |  71 ++
 tickets/T-4632/ticket.md                           |  41 +
 tickets/T-4633/done-report.md                      | 743 +++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 ++
 tickets/T-4634/ticket.md                           |  46 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  30 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 ++++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  59 ++
 tickets/T-4646/ticket.md                           |  31 +
 tickets/T-4647/ticket.md                           |  34 +
 tickets/T-4648/ticket.md                           |  28 +
 tickets/T-4649/done-report.md                      | 888 ++++++++++++++++++++
 tickets/T-4649/ticket.md                           | 105 +++
 tickets/T-draft-31fbe483/ticket.md                 |  34 +
 tickets/T-4748/ticket.md                 |  53 ++
 tickets/T-4751/ticket.md                 |  35 +
 tickets/T-4650/done-report.md            | 893 +++++++++++++++++++++
 tickets/T-4650/ticket.md                 | 166 ++++
 tickets/archive/T-0090/ticket.md                   |  18 +
 tickets/archive/T-0240/ticket.md                   |  18 +
 tickets/archive/T-0292/ticket.md                   |  18 +
 tickets/archive/T-0336/ticket.md                   |  18 +
 tickets/archive/T-0364/ticket.md                   |  24 +
 tickets/archive/T-0403/ticket.md                   |  18 +
 tickets/archive/T-0470/ticket.md                   |  17 +
 tickets/archive/T-0525/ticket.md                   |  18 +
 tickets/archive/T-0553/ticket.md                   |  18 +
 tickets/archive/T-0557/ticket.md                   |  18 +
 tickets/archive/T-0730/ticket.md                   |  18 +
 tickets/archive/T-0814/ticket.md                   |  26 +
 tickets/archive/T-1148/ticket.md                   |  18 +
 tickets/archive/T-1265/ticket.md                   |  18 +
 tickets/archive/T-1266/ticket.md                   |  18 +
 tickets/archive/T-1402/ticket.md                   |  18 +
 tickets/archive/T-1651/ticket.md                   |  11 +-
 tickets/archive/T-1746/ticket.md                   |  94 +--
 tickets/archive/T-2314/ticket.md                   |   9 +
 tickets/archive/T-2338/ticket.md                   |   9 +
 tickets/archive/T-2438/ticket.md                   |   9 +
 tickets/archive/T-2454/ticket.md                   |   9 +
 tickets/archive/T-2688/ticket.md                   |   9 +
 tickets/archive/T-2710/ticket.md                   |   9 +
 tickets/archive/T-3128/ticket.md                   |  28 +
 tickets/archive/T-3255/ticket.md                   |   9 +
 tickets/archive/T-3664/ticket.md                   |  11 +-
 tickets/archive/T-3665/ticket.md                   |  10 +-
 tickets/archive/T-3667/ticket.md                   |  11 +-
 uv.lock                                            |   2 +-
 653 files changed, 57790 insertions(+), 2103 deletions(-)
```

### Evidence
- `tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_empty_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_unrelated_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_additive_registry_change_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_destructive_registry_change_is_not_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_root_returns_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_frob_toml_returns_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFiles::test_configured_override_replaces_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFiles::test_malformed_value_falls_back_to_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFiles::test_is_registry_file_membership` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_non_registry_file_still_requires_declared_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_non_registry_path_is_never_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_pure_append_is_additive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_deleted_line_is_not_additive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_file_header_dashes_are_not_removed_lines` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_empty_diff_is_additive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_pure_append_is_additive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_deleted_line_is_not_additive` (pytest node id, verified passing when recorded)
- `tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_bad_ref_fails_closed` (pytest node id, verified passing when recorded)
