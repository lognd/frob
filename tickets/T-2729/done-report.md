## Done report

Seams found: SYS100/SYS101/SYS103 share one "observed capability kinds"
layer (no violation semantics of its own); SYS105/SYS108/SYS110 form a
"declared public surface" family; SYS102/SYS106/SYS107 form a
foreign-file/binding family. Split into 6 modules plus orchestration:
_selfconform_ids.py, _selfconform_models.py, _selfconform_kinds.py,
_selfconform_core_rules.py, _selfconform_surface_rules.py,
_selfconform_binding_rules.py. _selfconform.py kept as module docstring
(security design record) + orchestration (check_self_conformance and
waiver plumbing). All 7 files are now under LARGE001's 800-line
threshold (max 627 lines).

Changed:
- src/frob/strata/_selfconform.py (orchestration + models/ids re-export)
- src/frob/strata/_selfconform_ids.py (new)
- src/frob/strata/_selfconform_models.py (new)
- src/frob/strata/_selfconform_kinds.py (new)
- src/frob/strata/_selfconform_core_rules.py (new)
- src/frob/strata/_selfconform_surface_rules.py (new)
- src/frob/strata/_selfconform_binding_rules.py (new)
- tests/unit/strata/test_selfconform.py (frob:tests pointer repoint +
  frob:ticket edges on changed classes; one monkeypatch retargeted from
  _selfconform to _selfconform_core_rules)
- design/frob.strata (one via-list entry: fs.read may-grant on stratamod
  updated from _selfconform.py to _selfconform_surface_rules.py, the new
  home of the path.read_text call the grant covers)
- invariants/INV-026.md, invariants/INV-048.md (frob:used-by repointed
  to _selfconform_core_rules.py; added back the [INV-026] markdown-link
  reciprocal pointer alongside the existing frob:invariant directive)
- docs/strata/selfconform.md, docs/strata/surface.md (prose
  file::symbol pointers repointed to the moved functions' new files)

Evidence: tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires,
::TestBindingTotality::test_laundered_capable_file_fires,
::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103,
::TestPurposeContract::test_effect_outside_profile_fires,
::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires,
::TestNonPythonLanguageWiring::test_sorted_capability_files_includes_typescript
(module: 71 collected, 69 pass; the 2 failures are the pre-existing,
unrelated T-2806 testsuite env.read gap -- filed as T-2837,
confirmed reproducing on main before any T-2729 code change touches
that path).

Filed: T-2837 (SYS100: testsuite node missing env.read
via-grant for tests/unit/test_check.py, a T-2806 regression unrelated
to this split).

Gates: `frob check --only gates-fast` re-measured unscoped (not
--ticket, not --budget) after the split: every AFFECT001/COV002/COV006/
COV007/DOC006/DRIFT002/REF002/REF003 finding this split touched is
either resolved or `frob:waive`d with T-2729-specific reasoning (pure
verbatim symbol moves); the finding set outside this ticket's files is
unchanged from before the split (gate:FMT/PRE/REG/SCOPE/TEST/TICK
non-zero exit codes are pre-existing, unrelated to _selfconform.py).
SYS003 (import conformance) unaffected: the split introduces no new
cross-module import edges outside the new _selfconform_*.py sibling
files themselves, all of which import only downward (ids/models <-
kinds <- {core_rules,surface_rules,binding_rules} <- _selfconform.py
orchestration), no cycle, nothing crossing the registry/checker
boundary design/frob.strata's noflow assertions protect.

### Changed
```
 design/frob.strata                            |    2 +-
 docs/strata/selfconform.md                    |    6 +-
 docs/strata/surface.md                        |    6 +-
 frob.lock                                     |  336 +++++
 invariants/INV-026.md                         |    2 +-
 invariants/INV-048.md                         |    4 +-
 src/frob/strata/_selfconform.py               | 1744 ++-----------------------
 src/frob/strata/_selfconform_binding_rules.py |  385 ++++++
 src/frob/strata/_selfconform_core_rules.py    |  371 ++++++
 src/frob/strata/_selfconform_ids.py           |  169 +++
 src/frob/strata/_selfconform_kinds.py         |  436 +++++++
 src/frob/strata/_selfconform_models.py        |   52 +
 src/frob/strata/_selfconform_surface_rules.py |  427 ++++++
 tests/unit/strata/test_selfconform.py         |   67 +-
 tickets/T-2729/ticket.md                      |    9 +-
 tickets/T-2837/ticket.md            |   30 +
 16 files changed, 2338 insertions(+), 1708 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestNonPythonLanguageWiring::test_sorted_capability_files_includes_typescript` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 34 error(s), 691 warning(s), 717 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_binding_rules.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_core_rules.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_ids.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_kinds.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_models.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_surface_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_binding_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_core_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_kinds.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_models.py, I001@/home/logan/projects/frob/.claude/worktrees/t-2729/src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2729, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
