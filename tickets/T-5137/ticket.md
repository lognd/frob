---
id: T-5137
title: 'Automatic per-ticket agent token accounting from harness transcripts: zero
  model cost, bounded IO, one shared usage module, None for human work'
state: in-progress
kind: feature
origin: human
created: '2026-09-20'
priority: high
blocked_by:
- T-5132
parent: null
tier: story
sprint: v0.534.0
runs_last: false
milestone: 1.0.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_token_usage.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_leases.py
- .claude/hooks/*
- src/frob/stats/_agentic.py
- docs/modules/tickets-lifecycle.md
- tests/unit/test_token_usage.py
- tests/test_hook_dispatch_telemetry.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: true
scope_breadth_ack_reason: one new module plus the three touch points that call it
  (start, close/land, stats) and the hook that records session identity
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_token_usage.py
  reason: T-5137 needs its own evidence test file; not pre-declared in the ticket's
    original scope list
  actor: logan
  at: '2026-09-22'
- op: add
  glob: tests/test_hook_dispatch_telemetry.py
  reason: T-5137 adds transcript_path capture to the SessionStart hook; needs a positive-control
    test in its existing test file
  actor: logan
  at: '2026-09-22'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: declare _token_usage.py''s fs.read/fs.write capabilities
    on tickets_ledger and bump the via-count ratchet'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'SELFAUDIT001: declare _token_usage.py''s fs.read/fs.write capabilities
    on tickets_ledger and bump the via-count ratchet'
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '8'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
acceptance:
- text: given an agent session that started a ticket and landed it, when the land
    finishes, then the ticket carries input/output/cache token totals and the session
    id, with no model call made
  evidence: []
- text: given a session killed mid-ticket and a later land from the coordinator, when
    usage is collected, then totals reflect the transcript on disk and complete is
    False with a logged reason
  evidence: []
- text: given a human working a ticket with no recorded session, when the ticket closes,
    then usage is None and no warning claims zero tokens
  evidence: []
- text: given a 100 MB transcript already collected once, when usage is collected
    again, then only bytes past the cursor are read and the pass finishes under 2
    s
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5137
branch: t-5137
---
Owner directive 2026-09-20: token usage per ticket is set AUTOMATICALLY, never costs model tokens, never costs significant time, handles interrupted sessions, and lives in ONE abstraction (supersedes the manual --tokens flags sketched in T-5132's amendment). DESIGN. (1) Session identity capture, zero cost: a Claude Code SessionStart hook (stdin JSON carries session_id, transcript_path, cwd) appends one line {session_id, transcript_path, cwd, iso_ts} to .frob/sessions.jsonl; PostToolUse/Stop are NOT used (too chatty). frob ticket start/work records nothing new; the lease already has the worktree path and start time. (2) Collection at close and at land (whichever comes first, idempotent): frob.tickets._token_usage.collect_ticket_usage(root, ticket, lease) -> Result[TicketUsage | None, UsageError]: select sessions whose cwd is the ticket's worktree (or root when no worktree) and whose start is inside [lease.acquired, now]; for each transcript, stream the jsonl and sum message.usage.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens} over assistant entries with timestamp inside the window; per-transcript cursor {path, byte_offset, partial sums} cached in .frob/token-usage-cache.json so re-collection is incremental and a 100 MB transcript is read once. (3) Model: TicketUsage(pydantic, frozen): input, output, cache_creation, cache_read, sessions: tuple[str,...], transcripts_seen, window_start, window_end, collected_at, complete: bool. Ticket gains usage: TicketUsage | None; None means human or unmeasured and is valid forever; never write 0 for unmeasured (silent-zero lesson). (4) Edge cases, each a logged branch: session interrupted or killed -> transcript is still on disk, sum what exists and set complete=False when the last entry predates lease release; resumed session with the same session_id -> same transcript, cursor continues; several agents or sessions on one ticket -> sum across sessions and list them; transcript rotated, deleted or unreadable -> usage stays None with the reason logged, not an error; ticket requeued and restarted -> the window restarts at the new lease and earlier sessions are kept as a prior_windows entry; a session whose cwd is the shared root while working a ticket without a worktree -> attributed only if the ticket is the only in-progress ticket for that session's window, else left None with reason 'ambiguous'; subagent transcripts (Agent tool) nest under the parent session and are included when their path is under the same project slug. (5) One abstraction, no duplication: a HarnessAdapter protocol (transcript discovery + usage extraction) with the Claude Code adapter first; stats/_agentic.py's output_tokens_est stays a frob-output estimate but adopts the TicketUsage field names so flow, stats and sprint show render one shape. (6) Cost bounds: no model calls anywhere; hook append is O(1); collection is at most one streaming pass per new transcript bytes, capped at 2 s wall, beyond which it records complete=False and returns. (7) Reporting: frob ticket show prints usage; flow and sprint show add tokens per landed ticket and tokens per point.