## Done report

Changed:
scripts/fleet_status.py::_worktree_started_ticket_ids (new)
scripts/fleet_status.py::_START_TRANSITION_SUBJECT_RE (new)
scripts/fleet_status.py::_ticket_ids_state_verdict (new, ARCH001 split out of worktree_content_classification)
scripts/fleet_status.py::worktree_content_classification (ticket_id -> ticket_ids, generalized)
scripts/fleet_status.py::_print_worktrees_section (call site retargeted)
scripts/fleet_status.py::_worktree_ticket_id (docstring updated -- no longer a production call site)
docs/guides/coordinator-scripts.md (worktree_content_classification, _worktree_ticket_id, _print_worktrees_section sections updated; new _worktree_started_ticket_ids section)
tests/unit/test_coordinator_scripts.py (ticket_id= -> ticket_ids=[...] call sites; new TestWorktreeStartedTicketIds class; two new end-to-end
  TestWorktreeContentClassificationLiveGit tests; _init_bare_repo extracted, replacing 3 duplicate _init_repo methods)

Verified the claim before touching code: `git worktree list` against
this actual live fleet shows most real worktree names do NOT match
_TICKET_NAMED_WORKTREE_RE (^t-(\d+)$) -- fb-t2775, t2763-t2359,
t2766-t2764, fa-t2589-t2559, dev-friction, gate-internals,
rule-bookkeeping, land-integrity-series, reg-enforce, t1661-series,
t1860-series, t1893-t1908, t2747-t2746. worktree_content_classification's
`ticket_id=_worktree_ticket_id(name)` short-circuit silently resolved to
None for all of these, falling through to the raw content diff and
risking a false STRANDED/STALE verdict for genuinely active work -- the
same defect class T-2747 already fixed for the leases section
(_worktree_ticket_id -> _worktree_started_ticket), applied here to the
WORKTREES section's own classifier.

Fix: `_worktree_started_ticket_ids(path)` reads back EVERY ticket id a
worktree's own unlanded history (main..HEAD) structurally started, by
parsing frob.tickets._leases.commit_start_transition's own commit-subject
shape -- no naming assumption, and it returns every id for a series
worktree, not just one. worktree_content_classification's `ticket_id`
parameter became `ticket_ids: Sequence[str]` (plural): ACTIVE if ANY
resolved id is non-terminal (or queued-with-lease); STALE from ticket
state only if EVERY id resolved AND is terminal-with-landed land_commit
(a mix of landed+unresolved/unlanded ids must not force a false STALE).
Per the standing directive (parse structure, never match names): the
fix reads git commit history/subjects, never worktree directory names.

Positive controls (both directions):
- must-now-fire: TestWorktreeStartedTicketIds.test_non_conventionally_named_worktree_resolves
  (a "waive-liveness"-shaped worktree resolves its started id;
  _worktree_ticket_id on the same name returns None, confirming the old
  code path could never have found it) and
  .test_series_worktree_resolves_every_started_id (a "t2763-t2359"-shaped
  worktree resolves BOTH started ids, not just one).
- end-to-end must-now-fire:
  TestWorktreeContentClassificationLiveGit.test_non_conventionally_named_worktree_classifies_active_via_structural_ids
  -- a subject-named worktree holding a real in-progress ticket now
  classifies ACTIVE via the structural resolver (previously would have
  fallen through to the content diff and could misreport).
- must-still-pass / negative control:
  TestWorktreeStartedTicketIds.test_no_start_transition_commits_resolves_empty
  and .test_worktree_with_genuinely_no_ticket_is_not_force_matched -- a
  worktree that never ran frob ticket start/work resolves ticket_ids=[]
  and is never force-matched; the existing single-ticket-id test suite
  (210 tests total, including the pre-existing TestWorktreeContentClassification
  family) stays green unmodified in behavior.

Live smoke test: ran `uv run python scripts/fleet_status.py` against
this actual fleet (30+ real worktrees, several non-conventionally named)
-- no crash, WORKTREES section renders normally.

Filed: none new.

Gates: `frob check --ticket T-2755` clean of every ticket-attributable
finding after fixing ARCH001 (function-length split), 4x AFFECT001 (doc
updated in the same change), DOC002 (new anchor added), COV002 (frob:ticket
directives on every changed test symbol), SCOPE001 (scope widened to the
doc + test file, both genuinely touched), and DUP001+WIRE001 on a test
helper (consolidated 3 duplicate _init_repo copies into one module-level
_init_bare_repo, waived WIRE001 as a private test-fixture helper per the
existing tests/test_cache_gate.py precedent for the identical shape).
tests/unit/test_coordinator_scripts.py: 210/210 green (the one pre-existing
unrelated failure, TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked,
reproduces identically on main before this change -- confirmed, not
touched).

### Changed
```
 docs/guides/coordinator-scripts.md     |  53 ++++++-
 rapid-debt.jsonl                       |   9 ++
 scripts/fleet_status.py                | 188 +++++++++++++++++------
 tests/unit/test_coordinator_scripts.py | 262 ++++++++++++++++++++++++++++++---
 tickets/T-2755/done-report.md          |  99 +++++++++++++
 tickets/T-2755/ticket.md               |   6 +
 6 files changed, 544 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_non_conventionally_named_worktree_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_no_start_transition_commits_resolves_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_series_worktree_resolves_every_started_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_non_conventionally_named_worktree_classifies_active_via_structural_ids` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_worktree_with_genuinely_no_ticket_is_not_force_matched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 20 error(s), 983 warning(s), 712 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
