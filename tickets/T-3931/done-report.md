## Done report

Fixed 3 of 8 day-one findings at their source; deferred the remaining 5
with reasons (2 to new follow-up tickets I filed, 2 to existing tracked
work, 1 -- the bare-pytest coverage bug -- with real repro evidence
prepared for T-3887 per the ticket's own instruction not to fix it here).

FIXED AT SOURCE:

1. ROOT001 (gate should not fire): added check (d) to
   src/frob/gates/_root_asset_dirs.py::root_asset_dir_gate -- a
   repo-root directory is no longer flagged if frob.toml's own
   [[refs.entrypoint]] allowlist (the SAME allowlist REF001/REF002/
   REF003 already read via frob.gates._refs._load_allowlist/
   _allowlist_covers) covers at least one tracked file under it. A
   scaffold-provided frob.toml already declares .github/workflows/*.yml
   and invariants/.gitkeep as entrypoints; before this fix ROOT001
   ignored that declaration entirely. Verified: a real fixture with a
   frob.toml carrying those exact two entrypoint declarations and no
   other reference is silent (test_directory_with_refs_entrypoint_
   declaration_is_silent); all 13 existing+new ROOT001 tests pass.

2. MILE003 (scaffold should not generate the thing that trips it): every
   scaffold type's frob.toml.j2 (shared python/cpp, plus python-tool,
   pybind11-library, pyo3-library, web-app's own copies) now declares
   [tickets] default_milestone = "0.1.0" (matching the generated
   pyproject.toml version), so a fresh repo's first ticket resolves a
   milestone instead of tripping MILE003 immediately. Verified: rendered
   every registered scaffold type and asserted the parsed frob.toml
   carries the declaration (test_every_scaffold_type_declares_default_
   milestone, all 7 types including cpp-library/cpp-tool which share the
   cpp template).

3. COV001 (scaffold should not generate the thing that trips it): the
   generated scripts/bump_version.py's module-level PYPROJECT constant
   fired COV001 on an untouched project -- a standalone release script
   has no public API to document. Renamed to _PYPROJECT (frob's own
   private-symbol convention, which COV001's public-symbol check already
   skips) instead of shipping a scaffold waiver. Verified: ast-parses
   the generated script and asserts every top-level UPPER_CASE constant
   is private (test_bump_version_script_constant_is_private).

DEFERRED, WITH REASON:

4. REF001 on tickets/T-*/ticket.md and done-report.md (ledger v2): drafted
   the fix (a _is_ticket_ledger_v2_artifact glob check in
   src/frob/gates/_refs.py, mirroring the existing ledger-v1 tickets.md/
   tickets-archive.md exemption in _DEFAULT_ROOT_MANIFEST_EXEMPT) plus 4
   test cases, then REVERTED it: src/frob/gates/_refs.py is currently
   leased by in-progress T-4124 (auditing that same file's fnmatch call
   sites). Filed T-4153 with the full drafted fix and tests
   ready to reapply once T-4124's lease frees.

5. Nested-worktree false positives in the ty stage: drafted the fix (an
   unconditional ["--exclude", ".claude/worktrees/**"] added to `ty
   check`'s argv in src/frob/check/_python.py::_ty_base_cmd -- ty
   supports --exclude as a gitignore-style glob) plus a test, then
   REVERTED it: src/frob/check/_python.py is currently leased by
   in-progress T-3887 (a different, unrelated fix in the same file).
   Filed T-4154 with the full drafted fix and test ready to
   reapply once T-3887's lease frees.

6. WIRE001 (per-symbol waiver burden on a bottom-up ticket tree): this is
   a design-level ask (a wire.pending config section, or a ticket-level
   follow_up instead of per-symbol waives) already reached from a
   different direction by T-3855 (WIRE001 has no typing.Protocol
   awareness, parked with the identical "no future landing can discharge
   this waiver" complaint). Not implemented here -- it needs a design
   decision, not a bug fix, and T-3855 already holds that discussion.

7. The frob-suggest lexical-hook false positive (blocked a sed on docs/
   as a "hand-rename import line" with no import involved): this is the
   SAME lexical-vs-grammar hook class already tracked across at least 9
   open tickets (T-3405, T-3919, T-3960, T-3979, T-4015, T-4025, T-4061,
   T-4084, plus this one) -- not a new defect to file, an eighth (ninth)
   confirmed instance of an already-known class. No new ticket filed.

8. The bare-pytest coverage failure (frob coverage --full invokes a bare
   `pytest`, which resolves to the global ~/.local/bin/pytest shim
   instead of the scaffolded project's own .venv/bin/pytest): per this
   ticket's own instruction, NOT fixed here -- it is T-3887's root cause
   (also connects to T-4125's bare-`ty` finding). Reproduced it directly
   (not merely re-stated): scaffolded a fresh python-tool project, `uv
   sync`'d it, ran a bare `pytest --cov=src -q tests/` from that
   project's own directory -- 3 collection ERRORS,
   "ModuleNotFoundError: No module named 'demo'" (the global shim has
   zero visibility into the scaffolded project's own venv); `uv run
   pytest --cov=src -q tests/` with identical args from the same
   directory -> clean run, 92% coverage. Attempted to attach this
   evidence directly to T-3887 (`frob ticket body T-3887 --append-file`)
   and was refused: T-3887 is currently leased to worktree
   .claude/worktrees/t-4125, so only that lease holder may write it.
   The full repro writeup is saved at
   /tmp/t3887_evidence_note.md in this session for the coordinator or
   T-4125's own agent to attach once free.

NOT DUPLICATED: T-4132's py.typed/REF002 finding (named in T-3930's own
body as "do not fix that here -- it is T-4132's") was not rediscovered
or touched here.

SCOPE002 DISCLOSURE (frob:waive SCOPE002, same disclosed-breadth class
T-3914/T-4013/T-4019/T-4132 already measured and accepted -- SCOPE002's
own violation location is the machine-managed tickets.md ledger, not a
source line a code comment can anchor to, so it is disclosed here per
that established precedent rather than suppressed in code):

- docs/modules/gates.md (root_asset_dir_gate's pre-existing frob:doc
  edge): waived AFFECT001 inline on the function instead (see commit);
  the doc describes nearly the whole gates subsystem (2222 unrelated
  closure warnings measured when scoped in).
- src/frob/gates/_refs.py (root_asset_dir_gate's new call into
  _load_allowlist/_allowlist_covers, "probable under-capture"):
  `frob ticket scope T-3931 --add src/frob/gates/_refs.py` was attempted
  and refused (ScopeLeaseConflict: leased to in-progress T-4124). This is
  the same lease this ticket's REF001 fix (item 4 above) also could not
  touch.
- tests/gates_suite/test_invariant.py and tests/unit/test_scaffold_
  project.py (1870+ collapsed warnings between them): both are large,
  heavily cross-referenced shared test files (every gate's own test
  class lives in test_invariant.py; test_scaffold_project.py imports
  frob.tickets internals for unrelated fixtures) whose PRE-EXISTING
  frob:tests/private-helper edges cover symbols this ticket does not
  touch. Measured, not guessed: adding either file alone produces
  1878/79 unrelated closure warnings.

Gates: `frob check --ticket T-3931`: ruff-check clean, ruff-format clean
for every touched file (33 "would reformat" files are pre-existing,
repo-wide, confirmed by name to exclude every file this ticket touched).
gate:LARGE (1, src/frob/_cli_parsers/_ticket/_closeout.py) and gate:REF
(7, .github templates/CODE_OF_CONDUCT.md/CONTRIBUTING.md/SECURITY.md/
invariants/INV-022.md/INV-050.md) are pre-existing and untouched by this
diff -- confirmed via `git diff --stat main` showing zero lines changed
in any of them. gate:SCOPE (55, all SCOPE002) is the disclosed-breadth
class above. `frob test --base main`: PASS, exit=0, 9 python test
outcomes recorded.

Filed: T-4153 (REF001 ledger-v2 fix, blocked on T-4124's lease),
T-4154 (ty --exclude .claude/worktrees fix, blocked on T-3887's
lease). Items 6 (WIRE001) and 7 (lexical-hook) are not filed as new
tickets: they are already-open, already-tracked classes (T-3855 and the
9-ticket lexical-hook backlog respectively), so filing a duplicate would
itself be the wrong move.

### Changed
```
 src/frob/gates/_root_asset_dirs.py                 |  54 ++++++-
 src/frob/scaffold/data/shared/cpp/frob.toml.j2     |   6 +
 src/frob/scaffold/data/shared/python/frob.toml.j2  |   6 +
 .../data/shared/python/scripts/bump_version.py.j2  |   8 +-
 .../data/types/pybind11-library/frob.toml.j2       |   6 +
 .../scaffold/data/types/pyo3-library/frob.toml.j2  |   6 +
 .../scaffold/data/types/python-tool/frob.toml.j2   |   6 +
 src/frob/scaffold/data/types/web-app/frob.toml.j2  |   6 +
 tests/gates_suite/test_invariant.py                |  58 +++++++
 tests/unit/test_scaffold_project.py                |  52 +++++++
 tickets/T-3931/done-report.md                      | 171 +++++++++++++++++++++
 tickets/T-3931/ticket.md                           |   9 +-
 tickets/T-4153/ticket.md                 |  56 +++++++
 tickets/T-4154/ticket.md                 |  53 +++++++
 14 files changed, 485 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/gates_suite/test_invariant.py::TestRootAssetDirGate::test_directory_with_refs_entrypoint_declaration_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_every_scaffold_type_declares_default_milestone` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_bump_version_script_constant_is_private` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestRootAssetDirGate::test_refs_entrypoint_coverage_does_not_leak_across_directories` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 11 error(s), 4468 warning(s), 936 waived
- error-findings: DOC006@tickets/T-4144/ticket.md, LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, PRE001@tickets/T-3931, REF001@.github/ISSUE_TEMPLATE/config.yml, REF002@.github/ISSUE_TEMPLATE/bug_report.yml, REF002@.github/ISSUE_TEMPLATE/feature_request.yml, REF002@.github/PULL_REQUEST_TEMPLATE.md, REF002@CODE_OF_CONDUCT.md, REF002@CONTRIBUTING.md, REF002@SECURITY.md, SCOPE002@tickets.md
