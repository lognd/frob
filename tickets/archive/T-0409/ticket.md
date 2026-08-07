---
id: T-0409
title: 'Ledger-hygiene gate: enforce regular archiving (warn/fail when too many closed
  tickets sit un-archived)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/tickets/
- frob.toml
- tests/test_gates_tickets_hygiene.py
- .frob-release.json
- CHANGELOG.md
- docs/modules/tickets.md
- pyproject.toml
- tests/test_ticket_land.py
- tests/unit/test_ticket_runner_land_release.py
- tests/unit/test_ticket_store.py
- uv.lock
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_tickets_hygiene.py
  reason: TICK003 gate needs test coverage outside src/frob/gates|tickets scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/tickets.md
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'sequential single-worktree dispatch (T-0357/T-0338 done earlier, not yet
    landed to main): their committed files still show in the diff-vs-main SCOPE001
    checks against; cross-ticket exemption did not fire since those commit subjects
    did not literally name their ticket ids'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_collision.py
  reason: TICK003 fires against this repo's real un-archived-closed count when the
    test calls tickets_gate(Path("."), ...); isolate with tmp_path
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_below_warn_threshold_is_clean
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_warn_threshold_warns
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_open_tickets_never_count_toward_threshold
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_configurable_thresholds_from_frob_toml
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_malformed_frob_toml_degrades_to_defaults
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_never_writes_or_archives_anything
- tests/unit/test_ticket_store.py::TestClosedTicketIds::test_returns_done_and_dropped_only
- tests/unit/test_ticket_store.py::TestClosedTicketIds::test_orders_oldest_first
- tests/unit/test_ticket_store.py::TestClosedTicketIds::test_empty_queue_is_empty
- tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_no_violation_off_default_branch
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): we need a THING to ensure tickets get archived regularly -- not a habit to remember. Current state: tickets.md active ledger is 10,521 lines holding 61 closed (done/dropped) tickets un-archived (vs 99 genuinely open); frob ticket archive exists but NOTHING enforces running it, so it drifts (archiving has been DEFERRED repeatedly). Same class as the whole audit: an operation that should be enforced is left to discipline. FIX (per the meta-principle: a repeated "we got away with not doing X" is a frob enforcement gap): add a ledger-hygiene gate (TICK003-style) that makes stale un-archived closed tickets a build signal -- WARN when the active ledger holds more than a configurable threshold of closed tickets (default e.g. 20), escalating toward ERROR past a hard cap, with the fix being run frob ticket archive. Consider also: (a) frob ticket close/land optionally auto-archiving, or a frob ticket archive --stale that CI runs on a schedule; (b) an age dimension (a closed ticket older than N days un-archived). MUST be resurrection-safe: the known hazard is that archiving while worktrees are in flight lets a stale-base merge resurrect archived sections -- the gate should encourage archiving in QUIET windows (no active worktrees) and the land/splice path already has _drop_resurrected_ids + splice_ledger archive-resurrection guards which must stay sound. Ships per-project (T-0406) so every frob repo keeps its ledger honest. Acceptance: an active ledger with >threshold closed tickets reds/warns frob check naming the count + the archive command; after archive it clears; the gate is resurrection-aware (documented). Note: this is an instance of enforcing a maintenance obligation, sibling to the exhaustiveness registry T-0407.