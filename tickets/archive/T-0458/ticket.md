---
id: T-0458
title: 'never hand-edit tickets.md: frob ticket done-report/body/set commands for
  every field + daemon-backed serialized write pipe (infallible concurrent writes,
  race-free id allocation) so agents write the ledger like a regular file'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/app/ticket_runner.py
- src/frob/serve/
- src/frob/__main__.py
- docs/modules/tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestLedgerLock::test_two_threads_serialize
- tests/unit/test_ticket_store.py::TestLedgerLock::test_reentrant_in_same_thread
- tests/unit/test_ticket_store.py::TestAtomicWrite::test_no_partial_file_on_simulated_interrupt
- tests/unit/test_ticket_store.py::TestRaceFreeIdAllocation::test_concurrent_new_ticket_never_collides
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_composes_and_writes_atomically
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_second_call_replaces_first_report
- tests/unit/test_ticket_store.py::TestReplaceDoneReportSection::test_replaces_existing_section
- tests/test_tickets_evidence_cli.py::TestDoneReportCli::test_cli_composes_and_writes
- tests/test_tickets_evidence_cli.py::TestDoneReportCli::test_missing_why_exits_nonzero
- tests/unit/test_ticket_store.py::TestComputeChangedLines::test_non_git_root_returns_empty
- tests/unit/test_ticket_store.py::TestRenderChangedBlock::test_lines_rendered_fenced
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections
- tests/unit/test_ticket_store.py::TestLockPath::test_lock_path_under_frob_dir
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: writing directly to tickets.md is a hassle. Make a
WRITE-PIPE the canonical write tool for the ledger -- an agent writes to it
like a regular file, infallibly, and NEVER hand-edits markdown or tracks the
last ticket number itself. Refinement: the write-pipe is THE write mechanism,
not an optional daemon-up nicety.

Observed pain (this session, coordinator is the heaviest ledger user):
- No command sets a Done report (`frob ticket close` has --evidence but NO
  --done-report), so every close hand-edited tickets.md: awk/grep to find the
  block body-end before the next `<!-- ticket:T-#### -->` marker, an exact
  Edit that often hit "Found 2 matches" (non-unique scope blocks) or "file
  modified since read" (a parallel agent wrote concurrently), and cat-append
  fallbacks. Dozens of times. Same for scope/body edits.
- Id races: with ~30 parallel agents `frob ticket new` skipped/collided ids
  (a drainer once took T-0427); the coordinator reconciled numbers by hand.

DESIGN -- the write-pipe is THE write tool:
- SINGLE-WRITER INVARIANT: exactly one arbiter owns every byte of tickets.md.
  Nothing else -- not the CLI, not an agent, not an editor path -- ever writes
  the file directly. This single-writer property is what makes concurrent
  writes infallible (no interleaving, no lost update, no "modified since
  read"). Hand-editing the ledger becomes not just unnecessary but a lint
  error (a check that tickets.md was only mutated through the writer).
- ONE TYPED MUTATION PRIMITIVE: every ledger change is a structured,
  idempotency-keyed mutation submitted to the writer -- NewTicket, Transition
  (state), SetDoneReport, AddEvidence(dedup), ScopeAdd/Remove (T-0455),
  SetField (component/label/sprint/priority, T-0454), AllocateId. Each carries
  a client-generated mutation id; the writer DEDUPS on it, so a resend after
  an ambiguous failure is safe (retryable == infallible). The writer applies
  in receipt order, atomically (write-temp+fsync+rename, T-0456), and ACKS
  with the applied result (e.g. the allocated ticket id -- so the agent never
  guesses a number; the writer is the single id authority, race-free across
  all agents). `frob ticket new/close/done-report/scope/...` and agent SDK
  calls are all just CLIENTS that emit these mutations; NONE of them parse or
  edit markdown.
- CROSS-PLATFORM PIPE + DURABLE FALLBACK (same primitive, two transports):
  when the frob daemon is up (T-0321) it hosts the writer and exposes the pipe
  -- a unix domain socket on posix, a named pipe on windows, behind one small
  transport abstraction; it is created on server start and removed on server
  close, exactly the "intelligent pipe available when the server is up" the
  user describes; this is the FAST/warm path (shared, push-capable, T-0322).
  When the daemon is DOWN, the identical mutation lands in a lock-guarded
  append-and-apply journal (.frob/ledger-wal): the client appends the typed
  mutation under an exclusive lock and a short-lived local writer drains +
  applies + truncates. Same mutation type, same idempotency key, same atomic
  apply -- so the write tool works identically whether or not a server is
  running; the daemon only makes it warm and shared, never a correctness
  prerequisite. (This WAL is also the T-0456 intent-journal, reused not
  duplicated.)
- The T-0323 merge driver stays, but only for CROSS-checkout/branch merges
  (different worktrees reconciling their ledgers); same-checkout concurrency
  is fully handled by the single writer, so the driver is no longer the
  primary concurrency mechanism -- it is the offline/branch-merge one.

Acceptance:
- Closing a ticket with a Done report is ONE command, zero markdown editing;
  a lint fails if tickets.md is mutated outside the writer.
- Two agents concurrently emitting SetDoneReport + AllocateId (daemon up)
  never corrupt the ledger and never collide on an id; the same is true with
  the daemon DOWN via the WAL path; a resent mutation (simulated retry) is
  applied exactly once (idempotency-key dedup).
- After N concurrent closes, `git status` shows a clean, well-formed ledger;
  no agent ever hand-tracked or reconciled an id.
Relates: T-0321 (daemon host), T-0322 (push), T-0323 (branch-merge driver),
T-0455 (scope mutation), T-0456 (atomic writes + WAL/journal + reconcile),
T-0454 (fields the SetField mutation must cover).

REFINEMENT (user 2026-07-20): auto-fill the mechanical parts of the Done
report so the agent writes ONLY the narrative "why". frob already holds both
pieces at close time:
- PROOF / evidence: the ticket's recorded evidence ids (frob ticket evidence,
  already in the ledger) + each one's collected/passing status (D-01). The
  done-report mutation RENDERS this as the evidence section -- the agent never
  retypes node ids or pass counts.
- CHANGED section: `git diff --stat` of the ticket's own landing commit (or
  its scope-diff vs the base ref) -- the exact files+line deltas that shipped
  the ticket. The done-report mutation pulls this from git, not from the
  agent's memory (which is what dropped render.md / mis-listed files this
  session).
So `frob ticket done-report T-#### --why "<narrative>"` (or an interactive/
stdin body) COMPOSES: the narrative the agent supplies + an auto-filled
"Evidence" block (from recorded evidence + pass status) + an auto-filled
"Changed" block (from git diff --stat of the land commit). Everything
mechanical is generated and always accurate; the human/agent contributes only
the WHY. This kills both the hand-editing AND the class of errors where a
hand-written "changed"/"evidence" list drifts from reality (e.g. this
session's dropped-untracked-file and stale-evidence-id incidents). Ties T-0463
(land already computes the full changeset -> reuse it as the Changed source)
and D-01 (evidence pass status).