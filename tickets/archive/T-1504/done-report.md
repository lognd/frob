## Done report

Warning burn-down across TICK011/TICK007, COV remainder, REF, WALK, DEPR,
LANG, TODO, DEAD classes. Evidence cmd used throughout:
frob check --only <family> per class (per playbook 3b/3c foreground-timeout
discipline; combined multi-only calls used where noted).

Per-class before -> after (measured, gate:<X> summary line each time):

- TICK011: 21 -> 0. For each of the 21 disclosed-cut Done reports in
  tickets-archive.md with no ticket cited nearby, either added an inline
  citation to an already-existing real follow-up ticket (T-1051, T-1062,
  T-1108/T-1151/T-1152/T-1171/T-1186/T-1189 chains, T-1159, T-1171,
  T-1189, T-1318, T-1357), filed one new real follow-up
  (T-1505, "vet/resolvers: close remaining 3 structural
  points-to gaps (rust macro_rules, cpp ptr-to-member, kotlin
  operator-invoke) -- T-1063 residue"), or added an explicit
  no-ticket-needed reason for genuinely closed/false-positive
  disclosures (T-1040, T-1053, T-1113, T-1145, T-1179, T-1193, T-1260,
  T-1327, T-1338, T-1424, T-1456, plus T-1016's CHANGELOG.md residue and
  T-1056's fully-waived EXHAUST001). Several first passes placed the
  citation/reason outside TICK011's +/-300-char vicinity window
  (measured, not guessed -- confirmed via a small debug script calling
  _tick011_disclosure_hits/_tick011_first_uncited_disclosure directly)
  and needed a second, closer edit; final state re-measured clean (0
  TICK011 findings, confirmed twice).
- TICK007: 10 -> 10, NOT remediated. Every finding is a genuine open
  high-priority feature/bug/ux ticket sitting dispatchable and unleased
  (T-1205, T-1217, T-1220, T-1236, T-1243, T-1269, T-1271, T-1317,
  T-1350, T-1395) -- the rule's own remediation text offers "dispatch it
  or re-prioritize it". Dispatching a new agent mission is a coordinator
  action this single-ticket implementer role does not have tooling for;
  arbitrarily lowering priority on tickets that are legitimately still
  high priority (several are epic/security children with real scope)
  would misrepresent them just to silence the gate. Left for the
  coordinator to either dispatch this wave or make a deliberate
  re-priority call -- not fixed here, disclosed rather than worked
  around.
- TICK009: pre-existing on T-1504 itself (this ticket) from an
  initial overbroad src/**/docs/** scope; narrowed to the exact ledger +
  fix-site files actually touched as work progressed (final scope list
  below). One remaining TICK009 on T-1505 (the new vet
  follow-up, src/frob/vet/** legitimately matches >25 files for that
  future dispatch) -- accepted per SCOPE002's own "a ticket whose plan
  is genuinely package-wide may use the bare glob" doctrine.
- WALK001: 4 -> 0. src/frob/refactor/_scan.py::find_python_files rerouted
  through frob.excludes.walk_pruned (NOT iter_files, whose git ls-files
  fast path would silently skip untracked .py files a refactor is
  actively creating -- confirmed by a real test regression when I tried
  iter_files first, then fixed). src/frob/tickets/_store.py::_v2_glob/
  _v2_archive_glob and _renumber_v2.py::_v2_reference_files waived: each
  walks only the small, already-scoped tickets/ (or tickets/archive/)
  subtree with a fixed shallow glob, no nested build/vendor dirs to
  prune -- matches the gate's own small-bounded-walk escape hatch, same
  disposition already used for sibling walks in the same files.
- DEPR003: 4 -> 0. All 4 (docs_runner.py::_run_search, map_runner.py::run,
  outline_runner.py::run, xref_runner.py::run) already carried a
  "sunset rescinded" reason from T-1238's own 2026-07-29 directive, but
  the directive's sunset= field was never removed, so DEPR003 kept
  firing against a deadline that no longer applies. Waived each citing
  T-1238 (the open epic whose own acceptance criterion is to remove
  these frob:deprecated markers entirely once frob explore lands) --
  accepted debt until that epic closes, not a live migration deadline.
- REF: 9 -> 0. 3x REF001 (tickets/attachments/T-1433/0{1,2,3}-untitled.txt)
  exempted via new [[refs.entrypoint]] frob.toml entries -- each is
  referenced only via tickets-archive.md's own YAML attachments: path:
  field, a syntactic position REF001's auto-scan does not recognize. 2x
  REF002 (docs/audits/docs-staleness-2026-07-29.md,
  docs/audits/test005-zero-classification-t1418.md) fixed by adding a
  real second cross-reference from docs/audits/README.md and
  docs/index.md respectively. 4x REF003 (invariants/INV-002/011/029/041
  declaring frob:used-by on a file that no longer carries the real
  binding) fixed by repointing each frob:used-by at the actual file the
  T-1152/dup/sys/threat splits moved the frob:invariant/spec-link anchor
  into (_evidence.py, _dup.py, _sys.py, _threat_discharge.py) --
  confirmed via direct grep for the real anchor before repointing, and
  INV-041 needed a second correction (first guess, _sys_selfaudit.py,
  carries the bare frob:invariant INV-041 marker but not the
  backtick-path reverse-reference REF003 requires; _sys.py has both).
- TODO002: 1 -> 0. src/frob/gates/_docenum.py::_extract_members's
  frob:todo T-draft-323551f5 never resolved to a real ticket (never
  filed). Filed the real follow-up (T-1506, "docenum: widen
  _extract_members to resolve argparse choices=[...] lists") and
  rebound the directive to it.
- DEAD001: 1 -> 0. tests/unit/test_land_release_coherence.py::
  _no_real_subprocesses is a teardown-only pytest autouse fixture, the
  same false-positive class already waived for several sibling fixtures
  in this codebase (tests/test_dup_cross_lang.py, tests/test_serve_
  daemon.py, etc.) -- waived with the matching reason.
- LANG (lang_conformance): 0 -> 0, already clean at measurement time; no
  action needed.
- COV (coverage): introduced a REAL regression mid-ticket and caught it
  via the ticket-scoped check before finishing: touching find_python_
  files/_v2_glob/_v2_archive_glob/_v2_reference_files/_extract_members
  without a frob:ticket edge tripped COV002 (3 errors). Fixed by adding
  frob:ticket T-1504 to each touched function; re-measured
  gate:COV 0 errors both via --only coverage alone and via --ticket
  T-1504 --budget 100. COV006/COV007 WARN-tier remainder (29
  unwaived: 13 COV006 call-graph-reachability gaps, 16 COV007
  private-doc-anchor findings) spans ~15 files well outside this
  ticket's declared scope (app/_daemon_proxy.py, app/ticket_runner/
  _land_cmd.py, release/__init__.py, strata/_compliance.py, strata/
  _effects.py, strata/_selfconform.py, tickets/_land.py, tickets/
  _land_squash.py, tickets/_land_git_ops.py, vet/_capability.py,
  tickets/_store.py::_yaml_loader, app/__init__.py, test_daemon_proxy_*
  fixtures) -- NOT touched here. Widening scope that far for doc-anchor
  moves/test rebinds across ~15 unrelated files is a distinct unit of
  work; disclosing rather than scope-creeping. No follow-up ticket filed
  for this specific remainder (recording here per TICK011 discipline so
  a later Done report can cite this one) -- COV006/COV007 are WARN-tier
  advisory debt, not blocking.

Gates (measured):
- tickets family: 0 errors, 11 warnings (10 TICK007 + 1 TICK009 on the
  new follow-up ticket), 0 waived -- down from 34 warnings at start.
- coverage family: 0 errors, 30 warnings, 140 waived (was 0 errors
  before my edits too, but with a 3-error regression introduced and
  fixed mid-ticket, see above).
- refs family: 0 errors, 0 warnings, 50 waived -- down from 9 warnings.
- walk_lint family: 0 errors, 0 warnings, 23 waived -- down from 4
  warnings.
- deprecated family: 0 errors, 0 warnings, 13 waived -- down from 4
  warnings.
- lang_conformance family: 0 errors, 0 warnings throughout.
- ticket-scoped budget run: 1 error (PRE001, stale sweep after repeated
  scope widenings) -> fixed via the ticket sweep verb; re-verified
  prework family clean (0 errors, 0 warnings).

Coordinator extension: WAIVE004 stale-waiver drain

Merged main into the worktree (abd65912, clean, ancestor-verified) after
the coordinator confirmed the freshness precondition (main's suite green,
fresh coverage.xml, a full unscoped check already run there). Rebuilt
natives, then ran a full unscoped check (bare, no --only) per the
coordinator's explicit instruction -- sanctioned here because WAIVE004
structurally requires a full run to compute (frob.gates._waive: "only
ever fires on a full, unscoped run"), so no --only/--budget chunking can
produce its live list.

Before: gate:WAIVE 0 errors, 20 warnings, 0 waived (20 unique WAIVE004
findings, confirmed via grep -c against the deduped WARNING lines).

Per finding, checked whether the waived rule is in
frob.gates._waive.SCOPED_RUN_FLAKY_RULE_IDS ({SCOPE001, COV002, TODO001})
before touching anything:

- 8x SCOPE001 (src/frob/gates/__init__.py, _decisions_compliance.py,
  _doclink_docanchor.py, _sys.py, _tickets_gate.py, _todo_fmt.py,
  _waive.py, tests/test_gates.py, tests/test_tickets_gate_claim_evidence.py
  -- 9 sites, 8 in src/frob/gates/*): LEFT IN PLACE per the coordinator's
  explicit exception (SCOPE001 is scope/lease-dependent, not provably
  dead) -- added a dated review note to each reason string instead of
  deleting.
- 11 genuinely stale, DELETED (each rule confirmed NOT in the flaky set,
  and the gate's own WAIVE004 message text -- "match-absence here is
  meaningful, not a scoped-run artifact" -- backs the freshness claim):
  OPAQUE001 (src/frob/app/config.py::from_external), COV005
  (src/frob/app/stats_runner.py::_run_body), ARCH102
  (src/frob/graph/cache.py module docstring), PII012
  (src/frob/outline/__init__.py::_signature_from_tokens), EXHAUST001
  (src/frob/vet/_scan.py::_bounded_process_dependency), 3x REF002
  (strata-core/src/parse/grammar_{core,infra,node}.rs module docstrings),
  3x WIRE001 (tests/conftest.py::_dump_all_thread_stacks/
  _install_stackdump_handler, tests/unit/test_conftest_stackdump.py::
  _load_conftest -- all three carried a follow_up="T-1466" marker;
  T-1466 is still queued/open, but the waived RULE itself (WIRE001) is
  what the gate proved dead this run, independent of whether the broader
  T-1466 feature work is done).

After: gate:WAIVE 0 errors, 9 warnings, 0 waived (re-measured via the
same full unscoped check; the 9 remaining are exactly the 8
src/frob/gates/* SCOPE001 sites plus the 1 tests/test_gates.py SCOPE001
site left deliberately -- confirmed by diffing the before/after WAIVE004
line lists, not by count alone).

A ruff regression surfaced mid-sweep: the DEPR003 waiver reasons added
earlier in this ticket, and the new SCOPE001 dated notes, both pushed
several lines past E501's 88-char limit (5 files: docs_runner.py,
map_runner.py, outline_runner.py, xref_runner.py, gates/__init__.py,
plus the same note duplicated across 6 more gates/*.py files) -- caught
by this same full unscoped check (2 ruff-check errors), fixed by
wrapping each onto backslash-continued comment lines, re-verified ruff
check on all touched files clean.

Land-repair re-verification (2026-08-03, post-merge)

Merged main again (a5614dfe -> a53e2370, clean 3-way merge, main
verified as an ancestor of the new tip) as part of a land-repair pass,
rebuilt natives, and re-ran the checks this ticket's own findings depend
on against the merged tree:

- wire family: 0 errors, 0 warnings -- the WIRE001 finding this
  land-repair brief expected to have resolved after merging main (a
  helper only reachable post-merge) is confirmed clean; no waiver
  needed.
- tickets family: 0 errors, 2 warnings (TICK004 on T-1235, TICK009 on
  T-1505's intentionally-wide vet/** scope) -- no
  CrossTicketLeakage finding against T-1505/T-1506
  at this tree state; the two drafts the original brief named renumber
  at land as documented above, and the coordinator lands with
  --allow-cross-ticket per the brief.
- sys/ruff/archgate/invariant/pii_structural families: 0 errors across
  gate:ARCH, gate:LARGE, gate:PII, gate:SEC; ruff-check/ruff-format
  findings (2 warnings / 8 files) confirmed pre-existing repo-wide drift
  outside this branch's own diff against main, same set measured on
  sibling land-repair branches this session (tests/test_telemetry.py,
  tests/unit/strata/test_audit.py, src/frob/refactor/_alias_policy.py,
  src/frob/refactor/_prose.py, tests/test_refactor.py, tests/unit/
  strata/test_compliance.py, tests/unit/test_app_runners_batch6.py,
  tests/unit/test_daemon_proxy_error_paths_t1457.py).
- deletion-filter check (diff-filter=D against main): empty -- no
  unintended deletions carried forward by the merge.

No code changes were needed this pass; this is a re-verification-only
refresh of the gate state after merging main.

### Changed
```
 docs/audits/README.md                     |   1 +
 docs/index.md                             |   1 +
 frob.toml                                 |  12 +
 invariants/INV-002.md                     |   2 +-
 invariants/INV-011.md                     |   2 +-
 invariants/INV-029.md                     |   2 +-
 invariants/INV-041.md                     |   2 +-
 src/frob/app/config.py                    |   6 -
 src/frob/app/docs_runner.py               |   4 +
 src/frob/app/map_runner.py                |   4 +
 src/frob/app/outline_runner.py            |   4 +
 src/frob/app/stats_runner.py              |   5 -
 src/frob/app/xref_runner.py               |   4 +
 src/frob/gates/__init__.py                |   5 +-
 src/frob/gates/_decisions_compliance.py   |   5 +-
 src/frob/gates/_docenum.py                |   3 +-
 src/frob/gates/_doclink_docanchor.py      |   5 +-
 src/frob/gates/_sys.py                    |   5 +-
 src/frob/gates/_tickets_gate.py           |   5 +-
 src/frob/gates/_todo_fmt.py               |   5 +-
 src/frob/gates/_waive.py                  |   5 +-
 src/frob/graph/cache.py                   |   5 -
 src/frob/outline/__init__.py              |   4 -
 src/frob/refactor/_scan.py                |  35 +-
 src/frob/tickets/_renumber_v2.py          |   5 +
 src/frob/tickets/_store.py                |  10 +
 src/frob/vet/_scan.py                     |   6 -
 strata-core/src/parse/grammar_core.rs     |   4 -
 strata-core/src/parse/grammar_infra.rs    |   4 -
 strata-core/src/parse/grammar_node.rs     |   4 -
 tests/conftest.py                         |  11 -
 tests/test_gates.py                       |   4 +-
 tests/test_tickets_gate_claim_evidence.py |   4 +-
 tests/unit/test_conftest_stackdump.py     |   4 -
 tests/unit/test_land_release_coherence.py |   4 +
 tickets-archive.md                        |  73 ++--
 tickets.md                                | 675 ++++++++++++++++++++++++++++++
 37 files changed, 819 insertions(+), 120 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestFindPythonFiles::test_finds_py_files_and_skips_venv` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_pyproject_version_from_disk` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_already_coherent_is_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 876 warning(s), 754 waived
- error-findings: none (measured, zero errors)
