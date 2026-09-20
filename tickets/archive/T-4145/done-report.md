## Done report

Cleared the seven REF001/REF002 findings at the source, per T-3931's instruction: no per-file waivers. Added a new default exemption (_is_github_convention_file / _GITHUB_CONVENTION_EXEMPT / _GITHUB_CONVENTION_EXEMPT_GLOBS) to frob.gates._refs, following the exact precedent _DEFAULT_ROOT_MANIFEST_EXEMPT already set for pyproject.toml/frob.toml/package.json (T-3019/T-3031): GitHub's own community-health files and issue/PR templates are consumed by the GitHub platform by fixed path/directory convention, never by another tracked file's text, so REF001/REF002's "no/one in-repo anchor" premise never applied to them. This ships as code every consumer inherits, not a per-project frob.toml declaration.

Recorded decision on REF002 for non-code files: NO CHANGE to REF002's general scope -- it keeps applying uniformly to code and non-code files. The actual defect was never "REF002 fires on docs", it was "REF002 doesn't know a file's real consumer is an external platform reading by path convention". Blanket-exempting all non-code files would trade a narrow, real gap for a much bigger blind spot (a genuinely single-anchored, rotting design doc would stop being flagged for every frob-enabled project). Recorded in _refs.py's own module docstring plus inline on the new exemption block.

Split _closeout.py (922 lines) into _closeout.py (attach/block/unblock/close/reverify/review, ~400 lines) and a new _closeout_evidence.py (fail/evidence/drop/reopen/archive/restore/done-report/waive-audit/sweep-async, ~545 lines), mirroring T-1270's existing per-concern split precedent for this package. No behavior change -- __init__.py's re-exports keep the package's public surface identical; one test (test_ticket_restore.py) that imported a moved symbol directly from _closeout was updated to import from _closeout_evidence instead.

Added test coverage: tests/test_refs_gate.py::TestGithubConventionExempt with the must-fire fixture (all seven files pass with zero waivers, including config.yml's genuine zero inbound references), a must-stay-quiet fixture (a genuinely orphaned file still fires REF001), and a path-specificity fixture (a non-convention-path copy of a community file is still subject to the gate).

Self-gate error count after the fix, scoped to this ticket (frob check --ticket T-4145): gate:REF and gate:LARGE both report 0 errors -- the two families this ticket exists to fix. Remaining --ticket-scoped findings are pre-existing SCOPE002 closure-cascade debt in this same package (ref_gate's and the attach-parser's frob:doc anchors into hub docs docs/guides/agentic-workflow.md and docs/modules/gates.md fan out into 350+ further warnings when pulled into any ticket's scope, never terminating) and one unrelated DOC006 finding on a different ticket's (T-4144) file -- neither is part of this ticket's declared scope or acceptance criteria, and neither appears in CI's unscoped self-gate run (which has no active ticket context, so gate:SCOPE never runs there). Filed as its own ticket (T-4156, declared no-scope pending a remediation-approach decision) rather than chased here.

### Changed
```
 tickets/T-4145/ticket.md           | 464 ++++++++++++++++++++++++++++++++++++-
 tickets/T-4156/ticket.md |  42 ++++
 2 files changed, 503 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestGithubConventionExempt::test_standard_community_files_and_templates_pass_with_no_waivers` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestGithubConventionExempt::test_a_genuinely_orphaned_file_outside_the_convention_still_fires_ref001` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_restore.py::TestRestoreCli::test_restore_reason_flag_is_required_by_the_real_parser` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestGithubConventionExempt::test_non_convention_path_copy_of_a_community_file_still_subject_to_ref_gate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 4471 warning(s), 935 waived
- error-findings: DOC006@tickets/T-4144/ticket.md, SCOPE002@tickets.md, SELFAUDIT001@tests/test_refs_gate.py
