## Done report

Changed:
- src/frob/strata/_bootstrap.py (new) -- BootstrapComponent, BootstrapFlow,
  BootstrapModel, render_bootstrap_text, existing_design_files,
  derive_bootstrap_model, write_bootstrap_model
- src/frob/app/sys_runner.py -- _refuse_if_model_exists, _log_bootstrap_model,
  _run_init, run() dispatch +"init", module docstring/imports
- src/frob/app/config.py -- AppConfig.sys_init_check
- src/frob/app/_config_external.py -- wired sys_init_check into the
  CLI-external-config allow-list (WIRE001)
- src/frob/_cli_parsers/_misc.py -- _add_sys_init_parser, wired into
  _add_sys_parser, epilog examples
- docs/commands/sys.md -- new "frob sys init" section (anchor
  frob-sys-init-t-2910)
- design/frob.strata -- new f_strata_gates flow (stratamod -> gates, for
  _bootstrap.py's reuse of frob.gates._tracked_files.tracked_files),
  stratamod fs.write via-list += _bootstrap.py, testsuite exec via-list +=
  test_bootstrap.py, frob:ticket T-2910 added to stratamod/testsuite nodes
  and the new flow (COV002)
- docs/design/registry/capability-via-ratchet.lock.json -- bumped
  stratamod::fs.write 4->5 and testsuite::exec 197->198 (SYS111)
- tests/unit/strata/test_bootstrap.py (new) -- 11 unit tests
- tests/unit/test_app_runners_batch7.py -- TestSysInit (3 CLI-dispatch tests)

Design choice for `may=` (per the ticket's hard constraint): NEVER emitted,
not even commented out. `render_bootstrap_text` has no code path that reads
capability-observation data at all -- it only ever writes `module`, `node
... { code ...; }`, and `flow` lines. The generated file's own header states
this explicitly and tells the human to run `frob check --only sys` and act
on SYS100/SYS103 to declare `may=` by hand. Justification: an observed-
capability ceiling would always equal what the code already does on day
one, i.e. zero enforcement -- exactly the mistake `_sync_may.py`'s widening
auto-fix already made (T-2922 is unwiring its caller) and the reason this
ticket's parent epic (T-2920) exists. Omitting the suggestion (vs. printing
it commented out) was chosen over the "commented suggestion" alternative
because SYS100 already computes and reports the exact real capability set
per node once the model exists -- printing our own possibly-stale snapshot
of the same thing at generation time would duplicate that live computation
with no upkeep path, whereas the live gate output is guaranteed correct at
the moment the human reads it.

Foreign-repo measurement (per the ticket's requirement -- worked on a throwaway
copy under /tmp, never committed anything into /home/logan/projects/ssh-manager,
deleted the copy afterward):
- Repo: a fresh git snapshot of /home/logan/projects/ssh-manager (no
  design/, no .strata anywhere) copied to a scratch dir, `git init -q -b
  main && git add -A && git commit`.
- BEFORE: `frob check --only sys <repo>` -> "0 errors 0 warnings",
  sys=0.00s (nothing to check, no model at all).
- `frob sys init <repo>` -> "sys init: derived 2 node(s), 1 flow(s) from
  12 scanned file(s)": node ssh_manager_app <- ["src/ssh_manager/app/**"]
  (3 files), node ssh_manager_root <- ["src/ssh_manager/__init__.py",
  "src/ssh_manager/__main__.py"] (2 files); flow
  ssh_manager_root -> ssh_manager_app (2 import edges). Generated file:
  design/ssh_manager_copy.strata, 25 lines, 2 nodes, 1 flow, zero `may`
  lines.
- Must-produce control: fed the generated file straight through
  `frob.strata._parse.parse_module` + `frob.strata._elaborate.elaborate`
  (frob's own loader, not a fixture) -- both `Ok`, "elaborated module
  ssh_manager_copy: 2 node(s), 1 flow(s), 0 boundary(ies), 0 claim(s), 0
  refine(s)".
- AFTER: `frob check --only sys <repo>` -> FAIL, 11 errors (all
  SELFAUDIT001): 8x SYS100 (undeclared fs.read/fs.write/exec observed on
  ssh_manager_app -- real subprocess/file-write/file-read sites in
  app/app.py) + 3x SYS103 (three test files have observed capabilities --
  fs-read, env-read, exec -- with no node's code= glob binding them, since
  the bootstrap never touches tests/). Also 2 SYS002 warnings (no `may`
  keeps the auto-injected std.policy.analyzable secret construct unbound,
  expected with zero `may` declared).
- Honest reporting on SYS200-205/SYS003: NEITHER fired on this repo. It
  is a single small package with no duplicate port/path/pipe claims and
  no multi-writer store, and (after the fix below) no cross-component
  import crosses an undeclared flow direction either -- a bootstrap that
  produces a model nothing in that specific rule family fires on. What
  DOES fire immediately and usefully is SYS100/SYS103, which is exactly
  the "declare your may= by hand, node by node" on-ramp the ticket asks
  this command to create.

Bug found and fixed via this same foreign-repo measurement (not by
inspection): the FIRST pass at the single-top-package "root bucket" used
an `off-by-one` `len(segments) > 1` check that misclassified a loose file
directly in the package root (`src/pkg/__init__.py`, 2 segments) as if it
were itself a subdirectory, emitting a nonsensical `code
"src/pkg/__init__.py/**"` glob-of-a-file. Fixed to `> 2`. That fix then
surfaced a SECOND, more interesting bug: the naive fallback glob for that
root bucket (`src/pkg/*.py`) is unsound under `fnmatch.fnmatch`'s
semantics (frob's own `_code_binding.bind_code` matcher) -- `*` matches
`/` too, so `src/pkg/*.py` also matches `src/pkg/subdir/whatever.py` and
collides with that subdirectory's own `**` glob, producing
`AmbiguousCodeBinding` and disabling ALL of SYS003/SYS100/SYS107 on the
generated model entirely (silently, since it degrades to a WARN + skip,
not the visible error I initially assumed it would be -- caught by
actually running `frob check --only sys` against the generated file, not
by reading the code). Fixed by changing `BootstrapComponent.code_glob:
str` to `code_globs: tuple[str, ...]` and emitting one EXACT file path
per loose root file instead of a wildcard -- `_shrink.py`/`design/
frob.strata` already establish that a node's `code` line can carry
multiple space-separated quoted globs, so this reuses an existing
grammar shape rather than inventing one. A regression test
(`test_loose_file_directly_in_single_package_root_is_not_mistaken_for_a_subdir`)
covers the first bug; the fnmatch-collision fix is covered by the same
test asserting the exact-path-list shape plus the AFTER re-measurement
above (zero AmbiguousCodeBinding, real SYS100/SYS103 findings appearing
instead).

Control 1 (must-refuse, against frob itself): `frob sys init .` inside
this worktree (which already has design/frob.strata + 7 litmus files) ->
exit 1, "already has 8 .strata file(s) under design -- refusing to
overwrite an existing model ... use `frob sys shrink` ...", nothing
written (confirmed no new file appeared under design/).

Control 2 (must-produce, model-less repo): the ssh-manager-copy run above
-- generated file parses and elaborates cleanly through frob's own
loader.

Evidence: 14 pytest node ids (11 in tests/unit/strata/test_bootstrap.py
covering the pure derive/render module directly, 3 in
tests/unit/test_app_runners_batch7.py::TestSysInit covering the CLI
dispatch: write-a-model, --check-writes-nothing, refuse-when-model-
exists). All 14 observed passing via
`pytest tests/unit/strata/test_bootstrap.py
tests/unit/test_app_runners_batch7.py::TestSysInit -q` ->
"SUITE-RESULT: exitstatus=0 collected=14 failed=0"; bound via `frob
ticket evidence T-2910 <ids...>`.

Filed: none -- no out-of-scope discoveries needed a new ticket. The two
gates the SYS003/fs.write/exec changes touched (design/frob.strata's own
self-model, docs/design/registry/capability-via-ratchet.lock.json) were
added to this ticket's own scope rather than filed separately, since they
are direct, mechanical consequences of this ticket's own new code (a new
import + a new fs.write site + a new exec site in the test suite), not
independent work.

Gates: `frob check --only sys --ticket T-2910` clean (0 errors, 2
pre-existing warnings unrelated to this diff). `frob check --only
gates-fast --ticket T-2910` and `frob check --only archgate` show zero
findings anywhere naming _bootstrap.py/sys_runner.py::_run_init/the new
CLI wiring (WALK001 waived inline, matching _shrink.py's own precedent
for the identical design_root.rglob call; ARCH103 fixed by extracting
_refuse_if_model_exists/_log_bootstrap_model out of _run_init).
`frob check --land-parity` shows the SAME 18 unscoped errors before and
after this ticket's work, none referencing any file this ticket touched
(all pre-existing repo-wide debt: stale ticket attachments, tickets.md
TICK004, docs/guides/coordinator-scripts.md DOC006, etc.) -- confirmed by
grep against both land-parity runs.

### Changed
```
 tickets/T-2910/ticket.md | 78 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 78 insertions(+)
```

### Evidence
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel::test_refuses_when_a_strata_file_already_exists` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel::test_existing_design_files_lists_the_real_files` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelNeverEmitsMay::test_rendered_text_never_contains_a_may_line` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_single_top_package_splits_by_subdirectory` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_real_import_edge_becomes_a_flow_in_the_right_direction` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_test_files_are_excluded_from_component_derivation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_loose_file_directly_in_single_package_root_is_not_mistaken_for_a_subdir` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows::test_no_python_source_produces_an_empty_but_valid_model` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates::test_derived_model_parses_and_elaborates_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates::test_empty_model_still_parses` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_bootstrap.py::TestWriteBootstrapModel::test_writes_module_named_strata_file_under_design_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysInit::test_writes_a_model_for_a_repo_with_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysInit::test_check_prints_without_writing` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysInit::test_refuses_when_a_model_already_exists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 18 error(s), 793 warning(s), 856 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
