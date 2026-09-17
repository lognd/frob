## Done report

Fixed the 9 in-scope post-land sweep findings for T-4515's 4 code/test files (the 2 lease-file TICK010 warnings and the tests/unit/test_ci_self_gate_unscoped.py COV002 were scoped out -- lease files no longer exist on disk, WARN-only, and the test file collided with T-4534's in-progress lease on the same underlying work). AFFECT001 src/frob/lang/_project_detect.py and COV001/DOC002 on the same file: the module's existing frob:doc directives pointed at docs/modules/lang.md#unity-project-detection, a heading that never existed (T-4515 shipped the directives without ever writing the section) -- added the missing 'Unity project detection' section to docs/modules/lang.md describing detect_unity_project/UnityProjectInfo/UnityProjectDetectError, closing AFFECT001/COV001/DOC002 together since they were all downstream of the same dangling anchor. COV001 src/frob/excludes.py::UNITY_EXCLUDE_GLOBS: added a frob:doc edge plus the missing paragraph in docs/modules/app.md's existing 'Shared exclude-glob logic' section. COV007 src/frob/lang/_project_detect.py::_parse_editor_version: removed its own frob:doc directive (redundant -- its public caller detect_unity_project already carries the same anchor, which is what COV007 flags). COV002 tests/test_excludes.py and tests/unit/test_lang_project_detect.py, DUP002 tests/unit/test_lang_project_detect.py: resolved once frob check was run with --ticket T-4531 (this ticket's own scope glob covers both files) -- no code change needed, same measurement-base lesson as T-draft-357dade2/T-4532 (must pass --ticket and --base dev, not the coordinator's bare --files invocation). Verified: 'frob check --only coverage --only drift --only affect_drift --only clones --ticket T-4531 --base dev --files src/frob/excludes.py --files src/frob/lang/_project_detect.py --files tests/test_excludes.py --files tests/unit/test_lang_project_detect.py --files docs/modules/app.md --files docs/modules/lang.md' now reports 0 errors for all 6 of these files/rules (2 remaining errors in the run belong to .claude/hooks/frob-timeout-guard.py, unrelated pre-existing drift outside this ticket's scope). BUG002 waived per ticket body (gate/doc-metadata defect, not application code). ruff check/format clean on touched files (0 errors; the one pre-existing ruff-format warning is tests/test_tickets_triage_dates.py, untouched by this ticket). 2 pytest node ids bound as evidence (no acceptance-criteria array on this auto-filed sweep ticket), each run individually and passing.

### Changed
```
 docs/modules/app.md              | 12 ++++++++++++
 docs/modules/lang.md             | 33 +++++++++++++++++++++++++++++++++
 src/frob/excludes.py             |  1 +
 src/frob/lang/_project_detect.py |  1 -
 tickets/T-4531/ticket.md         | 25 ++++++++++++++++++++++---
 5 files changed, 68 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_lang_project_detect.py::test_detects_unity_project` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::TestUnityExcludeGlobs::test_unity_project_adds_globs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
