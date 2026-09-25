## Done report

Fixed the false-READY: --dry-run now builds the real staged squash preview
(compose_squash_in_disposable_worktree, pinned at root's pre-land tip) and
runs the same self-conformance/SYS111/DOC006 check
(_refuse_if_selfaudit_findings_in_touched_files) a real land's
_run_pre_commit_checks runs post-squash, right before the existing dry-run
early return in _land_locked -- so a clean dry run now proves the exact
class of refusal T-5302/T-5360 hit only at the real land. The disposable
worktree is always removed on exit; root and worktree are never mutated.

Blocked from updating docs/modules/tickets-landing.md in this same change:
that file's scope lease is held by in-progress T-draft-16f22785 (an
unrelated land --drain re-exec feature, ~22 lines, landing ahead of this
ticket in the queue per coordinator direction). Filing a small follow-up
ticket to add the dry-run squash-preview contract to that doc once the
lease frees, per playbook waiver guidance.

### Changed
```
 tickets/T-5403/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks::test_dry_run_refuses_on_a_planted_selfaudit001_sink` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks::test_dry_run_refuses_on_a_planted_doc006_pointer` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks::test_clean_worktree_dry_run_stays_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
