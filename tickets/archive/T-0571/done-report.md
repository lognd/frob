## Done report

T-0571's land was interrupted yesterday on branch
worktree-agent-a4f1c91fd4145fe43 (10 commits ahead of main at the time,
including b4646e32's commit-normalization fix); the branch never merged and
the ticket reverted to queued while main advanced ~70 lands, heavily
touching all three core files this ticket needs (ticket_runner.py,
tickets/__init__.py, _models.py via T-0832/T-0768/T-0754 and others). This
pass salvages that work by porting it onto current main rather than a
blind merge/cherry-pick, which would have conflicted throughout.

Ported (adapted line-numbers/context to today's shapes, semantics
unchanged from the donor):

- `frob.tickets._models`: `ReviewVerdict` (StrEnum: approve/reject),
  `ReviewEntry` (frozen BaseModel: verdict, reviewer, findings, commit,
  at), `Ticket.reviews: tuple[ReviewEntry, ...] = ()`, and three new
  `TicketError` members (`ReviewFindingsMissing`,
  `ReviewCommitUnresolvable`, `MissingApprovedReview`).
- `frob.tickets.__init__`: `load_require_review_for_close` (reads
  `[tickets] require_review_for_close` from frob.toml, default False),
  `_resolve_review_commit` (normalizes any --commit input to its full SHA
  via `git rev-parse`, T-0571 review round 2's fix -- never stores an
  abbreviated commit that could never satisfy the exact-match strict-mode
  check later), `record_review` (appends a ReviewEntry, rejects blank
  findings and unresolvable commits), `has_approved_review_for_commit`
  (the close --strict predicate). `_transition_guard`/
  `_done_transition_guard`/`transition` all gained an injected
  `reviewed: bool | None = None` parameter alongside the existing
  `covers_scope` (same D-02 injection pattern: `frob.tickets` stays free
  of the git/config dependency, the CLI computes the bool and passes it
  in). New public symbols added to `__all__`.
- `frob.app.ticket_runner`: `_current_commit` (shared `git rev-parse HEAD`
  helper), `_review` (the `frob ticket review` handler), and
  `_covers_review_for_ticket` (CLI-side strict-mode predicate: `None`
  unless BOTH `--strict` was passed on this close AND
  `require_review_for_close` is true in frob.toml). `_close` now computes
  `reviewed` the same way it already computes `covers_scope` and passes
  both to `transition`. `_close_failure_hint` gained a
  `MissingApprovedReview` case naming the remedy. Dispatch table and
  module docstring/usage string updated to list `review`.
- `frob.app.config.AppConfig`: `ticket_review_verdict`, `ticket_reviewer`,
  `ticket_findings_file` (Path), `ticket_review_commit`, and
  `ticket_close_strict` (bool, default False), wired through
  `from_external`'s str/path/bool field-copy loops.
- `frob.__main__`: `--strict` added to `frob ticket close`'s parser;
  `_add_ticket_review_parser` registers `frob ticket review <id>
  --verdict approve|reject --reviewer NAME --findings-file PATH
  [--commit SHA]`, wired into `_add_ticket_closeout_parsers`.
- `tests/test_tickets_review.py`: taken wholesale from the donor branch
  (`git checkout worktree-agent-a4f1c91fd4145fe43 -- tests/
  test_tickets_review.py`), unmodified -- all 17 tests pass against the
  ported implementation with no test-side changes needed.

Deviations from the donor branch:

- Docs: the donor's tickets.md changes (new "Structured review channel
  (T-0571)" section, `#structured-review-channel-t-0571` anchor, and the
  data-model additions) were NOT ported -- docs/modules/tickets.md is
  outside this ticket's declared scope (six files only, no docs file).
  The two `frob:doc` directives that pointed at the not-yet-existing
  `#structured-review-channel-t-0571` anchor were pointed at the existing
  `#public-api` anchor instead (the convention every other function in
  this module already uses), so no gate points at a section that does not
  exist. Filing the docs update is left as follow-up scope, not silently
  dropped -- flagging here per playbook section 8.
- `frob.lock`: the donor's scope list also touched `frob.lock`; not
  touched here (nothing in this port required a lockfile change, and
  worktree agents do not touch land-owned files per playbook section 4b).

Credits: donor commits 8fda39e1 (initial T-0571 implementation),
b4646e32 (commit-normalization fix, review round 2), and the intervening
9bdabd33/377219ab/1b967708/b1c59afd/e9acfd77/60ef4086 restore-ledger/
close/land housekeeping commits whose CODE content (not ledger state) this
port carries forward.

Verification: `uv run pytest tests/test_tickets_review.py` (17/17 pass),
plus the full touched-suite set (`test_ticket_land.py`, `test_tickets.py`,
`test_gates_tickets_hygiene.py`, `test_ticket_done_report_claims.py`,
`test_ticket_journal.py`, `test_ticket_leases_cross_worktree.py`,
`test_ticket_merge_driver.py`, `test_ticket_reconcile.py`,
`test_ticket_runner_archive_force.py`, `test_ticket_runner_quiet.py`,
`test_tickets_acceptance.py`, `test_tickets_brief.py`,
`test_tickets_cmd_evidence.py`, `test_tickets_collision.py`,
`test_tickets_dispatch_stale.py`, `test_tickets_evidence_cli.py`,
`test_tickets_lease.py`, `test_tickets_lease_overlay.py`,
`test_tickets_leases.py`, `test_tickets_ledger_concurrency.py`,
`test_tickets_organization.py`, `test_tickets_priority.py`,
`test_tickets_scope_mutation.py`, `test_app.py`, `tests/unit/test_app.py`,
`tests/unit/test_app_runners.py`, `tests/unit/test_ticket_file_flags.py`,
`tests/integration/`) all green, no regressions. `ruff check`/`ruff
format --check` clean under both PATH ruff and `uv run ruff`.
`frob check --ticket T-0571` (chunked lint/static/gates-fast) came back
0 attributable errors after refreshing the pre-work sweep
(`frob ticket sweep T-0571`, PRE001 was stale from the scope additions).

### Changed
```
 src/frob/__main__.py          |  56 +++++-
 src/frob/app/config.py        |  18 ++
 src/frob/app/ticket_runner.py | 136 ++++++++++++-
 src/frob/tickets/__init__.py  | 203 +++++++++++++++++--
 src/frob/tickets/_models.py   |  51 +++++
 tests/test_tickets_review.py  | 454 ++++++++++++++++++++++++++++++++++++++++++
 tickets.md                    |  61 +++++-
 7 files changed, 949 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_blank_findings_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_multiple_reviews_append_only` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_unresolvable_commit_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_short_sha_normalized_to_full_sha` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestHasApprovedReviewForCommit::test_true_only_for_matching_approve` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_defaults_false_with_no_frob_toml` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_true_when_configured` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestLoadRequireReviewForClose::test_false_when_absent_from_section` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestReviewCli::test_cli_writes_review_record` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestReviewCli::test_cli_requires_all_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_blocks_close_with_no_review` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_blocks_close_with_stale_approve_review` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 17 passed (from 17 evidence id(s))
- gates: 0 error(s), 1195 warning(s), 248 waived
