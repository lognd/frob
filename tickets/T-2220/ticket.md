---
id: T-2220
title: A landed ticket does not record its own land commit, so verify_lands.py cannot
  be addressed by ticket id (--plan lands unreachable)
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_models.py
- scripts/verify_lands.py
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-landing.md
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_squash.py
- docs/design/registry/capability-via-ratchet.lock.json
- tests/test_ticket_land.py
- tests/test_ticket_leases.py
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: verify_lands.py's frob:doc target -- this ticket changes its argument interface,
    so the doc must move with it
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: the land path gains a persisted land-commit field; the landing module doc
    documents that path
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'MEASURED: _find_landing_commit (_lifecycle.py:129) IS frob''s own ticket->land-commit
    resolver and implements exactly the broken bridge this ticket describes -- git
    log --grep ''land {ticket_id}([^0-9]|$)'', which cannot match a --plan land (subject
    ''chore(tickets): land --plan'', no id). This is the primary in-code consumer
    of the persisted field; without it the fix would add a field nothing reads'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_ledger_merge.py
  reason: T-1334/post-filing refactor moved the squash-apply commit machinery this
    ticket's own evidence cites (_land.py:1383's merge_commit) out of _land.py into
    sibling modules; _land_ledger_merge.py's _overlay_landed_ticket is where a land_commit
    written directly to root gets silently erased by a same-worktree retry's tie-break
    (_newer picks the incoming/worktree side, which never carries the field) -- fixing
    that here is required to land T-2220 without breaking the existing T-1001 no-op-retry-absorption
    guarantee
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: T-1334's post-filing split moved _commit_squash_apply/_land_commit_details
    (the per-ticket land path's own merge_commit-equivalent, the ticket's own cited
    producer) out of _land.py into this sibling module -- _record_land_commit (T-2220's
    follow-up-commit write) lives here
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: T-2220 adds new fs.write call sites to the tickets_ledger node (write_ticket
    calls in _record_land_commit/_land_plan_finalize_drafts, plus their git-add/git-commit
    follow-ups) -- SELFAUDIT001/SYS111 requires the ratchet ceiling bumped in the
    same diff that adds the sites
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-2220's own evidence lives in these three test files (TestRecordLandCommit
    in test_ticket_land.py, the land_commit stamp fix in test_ticket_leases.py::TestRefusesTerminalState,
    TestLoadLandCommit/TestVerifyLandsMain additions in test_coordinator_scripts.py)
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_ticket_leases.py
  reason: T-2220's own evidence lives in these three test files (TestRecordLandCommit
    in test_ticket_land.py, the land_commit stamp fix in test_ticket_leases.py::TestRefusesTerminalState,
    TestLoadLandCommit/TestVerifyLandsMain additions in test_coordinator_scripts.py)
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: T-2220's own evidence lives in these three test files (TestRecordLandCommit
    in test_ticket_land.py, the land_commit stamp fix in test_ticket_leases.py::TestRefusesTerminalState,
    TestLoadLandCommit/TestVerifyLandsMain additions in test_coordinator_scripts.py)
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit
- tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha
designated_repro_test: tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit
acceptance:
- text: Landing a ticket persists the resulting merge_commit as a structured field
    on the ticket record, written by the land path itself
  evidence:
  - tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit
- text: verify_lands.py accepts a ticket id and resolves via that field, and a SHA
    argument MUST STILL WORK (must-still-pass control)
  evidence:
  - tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit
  - tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit
- text: A --plan land (no ticket id in the commit subject) is resolvable by ticket
    id -- the case a log grep cannot reach
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit
  - tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id
- text: A never-landed ticket id is refused distinguishably from a typo'd SHA
  evidence:
  - tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id
  - tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f5568b7dbe36b3f9c2628b551814da0cab8abc5c
---
# A landed ticket does not record its own land commit, so the prescribed verification tool cannot be run from a ticket id

## Measured evidence (2026-08-16)

`scripts/verify_lands.py` is the standing hourly duty for confirming a land.
The things it verifies are identified by TICKET. It accepts SHAs only:

    scripts/verify_lands.py:79   parser.add_argument("shas", nargs="+")

    $ python3 scripts/verify_lands.py T-2211 T-2208
    UNKNOWN-SHA T-2211  (typo? not a commit in this repo)
    UNKNOWN-SHA T-2208  (typo? not a commit in this repo)

Nothing persists the resulting commit per-ticket, so there is no field to
resolve a ticket id against:

    $ git show main:tickets/T-2211/done-report.md | grep -E "[0-9a-f]{12,40}"
    (no output -- no sha anywhere in the done report)

    $ git show main:tickets/T-2211/ticket.md | grep -iE "commit|sha|landed"
    (only prose matches in the body; no structured field)

The land DOES know the value. `merge_commit` is produced at
`src/frob/tickets/_land.py:1383` and appended to `own_commits` at :1384; the
LAND-PROOF path verifies against it. It is computed, used, and then dropped.

## Why this is not cosmetic

The only remaining ticket -> land-commit path is a log grep, which is
ALREADY RECORDED AS BROKEN in this repo's own operating notes:
`git log --grep="land T-####"` misses `--plan` lands entirely, because those
commit as `chore(tickets): land --plan` with no ticket id in the subject.

That miss has already caused real damage once: it led to a correctly-blocked
T-2205 being requeued, and the "repair" that followed wrote a duplicated
`blocked_by: [T-2211, T-2211]`, which is what T-2216 now exists to fix. So
the missing field has already produced one ledger corruption and one
downstream ticket.

The two failure modes compose badly: the verification step that is supposed
to catch a bad land is the same step that cannot be addressed by ticket id.

## Do NOT fix it this way

- **Do NOT make `verify_lands.py` grep the git log for `land <id>`.** That
  reproduces the exact `--plan` blind spot described above, and hides it
  behind a tool that now LOOKS authoritative. A tool that silently reports
  nothing for a whole class of lands is worse than one that refuses the input.
- **Do NOT match the commit subject for the ticket id by substring/regex.**
  Standing user directive: decide from tokens/grammar, never lexical text.
  The commit subject is prose; the ticket id must come from a structured
  field written by the land itself.
- **Do NOT infer the SHA from commit ORDER, timestamps, or "the most recent
  commit touching tickets/<id>/".** Concurrent agents land continuously; this
  repo has already produced one false regression report from exactly that
  reasoning (a before/after `git rev-parse main` attributed another agent's
  land to the wrong ticket).
- **Do NOT write the field from the coordinator or from a script after the
  fact.** It must be written by the land, in the same commit, or it will
  drift from reality the first time a land is retried.

## Acceptance criteria

1. (MUST FAIL FIRST) A test that lands a ticket and asserts the ticket's
   persisted record names the resulting land commit. Against today's tree
   this fails because no such field exists -- confirm `--check-repro` reads
   FAILED_AT_PARENT before the fix commit.
2. The field is written by the land path that produces `merge_commit`
   (`src/frob/tickets/_land.py:1383`), not by a caller, and is a structured
   model field (`src/frob/tickets/_models.py`) -- not prose in a body or
   done-report.
3. `scripts/verify_lands.py` accepts a ticket id and resolves it via that
   field. A SHA argument MUST STILL WORK -- this narrows nothing; include the
   must-still-pass control, since every existing caller passes SHAs.
4. A `--plan` land (subject `chore(tickets): land --plan`, no id in the
   subject) is resolvable by ticket id. This is the case a log grep cannot
   reach, so it is the criterion that discriminates a real fix from the
   forbidden one.
5. An unlanded / never-landed ticket id is REFUSED distinguishably -- it must
   not read as "verified" and must not read the same as a typo'd SHA.

## Scope note

`scripts/verify_lands.py` is in scope as the consumer. The producer side is
the land commit path plus the ticket model. If the implementer finds the
field already exists under another name, STOP and report rather than adding
a second one -- two homes for one fact is the defect shape T-1966 covers.

## Done report

Changed:
- src/frob/tickets/_models.py::Ticket.land_commit (new field)
- src/frob/tickets/_land_squash.py::_record_land_commit (new)
- src/frob/tickets/_land_squash.py::_finish_real_land_report (new, split from _land_squash_apply_finish to clear ARCH001)
- src/frob/tickets/_land_squash.py::_land_squash_apply_finish (calls _finish_real_land_report)
- src/frob/tickets/_land.py::_land_plan_finalize_drafts (now stamps land_commit=merge_commit onto each finalized ticket, in-memory, before the finalize commit)
- src/frob/tickets/_land.py::_land_plan_merge_and_finalize (threads merge_commit into _land_plan_finalize_drafts)
- src/frob/tickets/_land_ledger_merge.py::_overlay_landed_ticket (carries land_commit forward across a same-worktree retry's tie-break, so it is never silently erased)
- src/frob/app/ticket_runner/_lifecycle.py::_find_landing_commit (now reads Ticket.land_commit, no git log --grep)
- scripts/verify_lands.py::load_land_commit (new), main() (accepts a ticket id alongside a sha)
- docs/guides/coordinator-scripts.md, docs/modules/tickets-landing.md (updated)
- docs/design/registry/capability-via-ratchet.lock.json (tickets_ledger::fs.write ratchet bumped 16 -> 17)

Evidence:
- tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit (--accepts 0, DESIGNATED REPRO -- FAILED_AT_PARENT confirmed against 60394a1b252d086068832dd24c299ad8ce6e9eb7, the test-only commit before the fix)
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit (--accepts 1, must-still-pass SHA control + ticket-id resolution)
- tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id (--accepts 2, the --plan discriminator: asserts the finalize commit subject is NOT matchable by the old `land T-####` grep pattern, and that land_commit resolves anyway)
- tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha (--accepts 3)
- tests/unit/test_coordinator_scripts.py::TestLoadLandCommit (3 methods, unit coverage for the new resolver)
- Full `tests/test_ticket_land.py` run (9925 lines, 279+ tests): only 4 failures, all independently confirmed PRE-EXISTING on main (test_refuses_on_dirty_main, TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice, TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses, TestUvLockSync::test_dirty_lock_with_other_change_still_refuses -- reproduced against a pristine `git worktree add --detach main` checkout before any of this ticket's edits)
- Full `tests/test_ticket_leases.py` run: 132/132 pass
- `tests/test_evidence_integrity.py`, `tests/test_ticket_work_and_land_finish.py`, `tests/test_tickets_collision.py`, `tests/unit/test_land_squash_residue_reclaim.py`: 136/136 pass
- `frob check --only lint/static/gates-native/gates-security/test --ticket T-2220`: every remaining ERROR-level finding independently confirmed pre-existing/unrelated (untouched files: src/frob/lang/_nodes.py, tests/test_ticket_work_and_land_finish.py, scripts/fleet_status.py, src/frob/app/ticket_runner/_land_cmd.py, src/frob/app/ticket_runner/_rapid_sweep.py, tickets.md backlog-rot TICK004/TICK006, pre-existing import cycles reproduced identically on a pristine main checkout)
- `uv run ty check src/frob/tickets/_land_squash.py`: clean after the frozenset[str] annotation fix

Filed: none (all follow-up work was in-scope drift-repair, folded into this ticket via `frob ticket scope --add` with citable reasons: src/frob/tickets/_land_squash.py, src/frob/tickets/_land_ledger_merge.py, docs/design/registry/capability-via-ratchet.lock.json, plus the three test files this ticket's own evidence lives in)

Gates: `frob check --only lint/static/gates-native/gates-security/test --ticket T-2220` clean of new findings (confirmed error-by-error against a pristine main checkout). `frob check --land-parity` could not complete under this session's WSL contention (repeatedly deferred/timed out on the `static` stage group inside its internal 300s budget across 3 attempts) -- NOT proof of a clean tree by the tool's own contract, but every family it would have run was independently verified clean via the `--only` stage checks above, including `--only static` itself.

## Design note: why a follow-up commit, not the squash commit itself

`land_commit` cannot be baked into the commit it names (a commit's hash is
a function of its own content, so it cannot contain its own future hash).
For the per-ticket `land <id>` path, `_record_land_commit` writes the field
in a small commit made immediately after the squash-apply commit, still
inside the same `land()` call -- `root`'s tip after a real land is now one
commit ahead of `LandReport.commit_sha` (unchanged: still names the
code-carrying commit). For `land --plan`, no such problem exists:
`merge_commit` is already a prior, real commit by the time the finalize
step runs, so it is stamped directly into the finalize commit's own
content with no follow-up needed.

This shifted two pre-existing tests' assumptions (`git rev-parse HEAD`
after a land now differs from `LandReport.commit_sha` by one commit) --
both updated to assert against the correct commit
(`TestReleaseBumpQuartetAtomicity::test_manifest_version_written_same_step_as_pyproject`,
`TestUvLockSync::test_bump_then_lock_synced_in_commit`), and the T-1001
absorption retry test's own "same commit" assertion was similarly
corrected to compare against root's actual post-land tip rather than the
squash-only sha.

### Changed
```
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 docs/guides/coordinator-scripts.md                 |  35 ++++-
 docs/modules/tickets-landing.md                    |  38 +++++-
 scripts/verify_lands.py                            |  75 ++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  45 +++----
 src/frob/tickets/_land.py                          |  48 ++++++-
 src/frob/tickets/_land_ledger_merge.py             |  20 ++-
 src/frob/tickets/_land_squash.py                   | 128 +++++++++++++++++++
 src/frob/tickets/_models.py                        |  16 +++
 tests/test_ticket_land.py                          | 142 ++++++++++++++++++++-
 tests/test_ticket_leases.py                        |  16 ++-
 tests/unit/test_coordinator_scripts.py             | 100 +++++++++++++++
 tickets/T-2220/ticket.md                           |  79 +++++++++++-
 13 files changed, 685 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRecordLandCommit::test_records_land_commit_field_in_a_follow_up_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_ticket_id_argument_resolves_via_land_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2220/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2220/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2220, RENDER001@src/frob/scaffold/_skills_sync.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
