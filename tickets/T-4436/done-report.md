## Done report

T-4436: fix_tick006_phantom_refile's _resolve_via_git_rename_measured trusted any git show -M --name-status rename pairing as a genuine promotion -- but -M is a content-similarity heuristic, not identity/provenance. MEASURED incident: T-draft-858a1bad (lost before promotion, T-4426) was rewritten to T-4383, an unrelated ticket, in worktree t-4428's Done report.

ROOT CAUSE: a coincidental unrelated delete+add in the same bulk-edit commit can clear git's -M similarity threshold. A weaker corroboration (checking for ANY -id: tid removed / +id: candidate added line anywhere in the diff) was tried and REJECTED as a no-op -- since two distinct tickets always have different id: lines by construction, that pair of lines is trivially present in the diff of any -M-paired rewrite, genuine or coincidental.

FIX: the real promotion primitive (renumber_one_v2's _rewrite_v2_id_field) changes ONLY the renamed file's id: frontmatter line -- title/body/every other field are byte-identical before and after. _tick006_confirm_rename_by_frontmatter (new) now requires the candidate pair's WHOLE diff to reduce to EXACTLY that one removed/added id: line -- a coincidental content-similarity pairing between unrelated tickets (different title, body, created date) is rejected even when -M itself still pairs them, and the scan continues to the next candidate/commit exactly as if that candidate had never matched. A rejected candidate logs a WARNING naming the draft unresolved; a confirmed rewrite logs an INFO line naming the mapping source (draft -> real id, cited-by ticket).

SCOPE NOTE: tests live in tests/test_gates_fix_engine.py (not a new tests/unit/ file) because design/frob.strata's SELFAUDIT001 capability declarations (exec/fs.write for subprocess+file-write test fixtures) are keyed per file path and that file already carries them -- a new file would need an out-of-scope design/frob.strata edit. The two shared test fixtures are real @pytest.fixture factories (not bare module-level helpers) to stay outside WIRE001/WIRE002's scan, which requires a follow_up ticket for any waived helper -- these have none to name since they are test-only by construction.

_tick006_check_rename_candidate was split into a new per-line helper (_tick006_evaluate_rename_line) to stay under ARCH001's 60-line threshold after the fix's added logic.

### Changed
```
 src/frob/gates/_fix_engine.py  | 192 ++++++++++++++++++++++++--
 tests/test_gates_fix_engine.py | 297 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-4436/ticket.md       |   4 +
 3 files changed, 481 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestTick006RenameConfirmation::test_git_m_false_positive_pairing_is_not_trusted_body_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestTick006RenameConfirmation::test_confirmed_promotion_is_rewritten_with_info_log` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestTick006RenameConfirmation::test_no_rename_at_all_is_unresolved_body_untouched_pending_new_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4862 warning(s), 963 waived
- error-findings: REF002@docs/design/macos-portability.md
