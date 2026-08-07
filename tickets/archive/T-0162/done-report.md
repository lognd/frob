## Done report

Changed:
- src/frob/tickets/_provisional.py (new): on_default_branch, mint_draft_id, is_draft_id, DRAFT_PREFIX
- src/frob/tickets/__init__.py: _allocate_ticket_id (new_ticket now mints a draft id off the default branch), renumber_one (new), finalize_draft (new)
- src/frob/tickets/_models.py: RenumberReport (new)
- src/frob/tickets/_store.py: _TICKET_ID_RE (marker/filename regexes now accept T-draft-<hex> alongside T-####, fixing a real bug found while writing the concurrent-worktree test -- draft ids silently vanished from the ledger without this)
- src/frob/gates/__init__.py: tickets_gate, _tick001_duplicate_ids, _tick002_draft_on_default (TICK001/TICK002, both added to _UNWAIVABLE_RULES); "tickets" added to _ALL_GATES/_build_jobs/_KNOWN_GATE_RULES
- src/frob/app/ticket_runner.py: _renumber now dispatches to _renumber_one (frob ticket renumber <old> <new> [--dry-run]) or the legacy whole-ledger renumber (no args)
- src/frob/app/config.py, src/frob/__main__.py: CLI wiring for renumber <old> <new> --dry-run (scope extended to include __main__.py, the CLI wiring the ticket's own renumber requirement required)
- tests/test_tickets_collision.py (new): reproduces all three incidents plus the concurrent-worktree invariant end-to-end (real git worktrees, real merge)
- tests/system/test_cli_ticket_worktree_root.py: updated to assert against whatever id frob ticket new actually mints (a linked worktree is always off the default branch, so this suite now exercises draft-id minting incidentally)
- docs/modules/tickets.md: "Provisional ids" + "Decision record: T-0162" sections, "Agent workflow implications (T-0162)" section, Design decisions/Integration points/CLI list updated

Decision: provisional ids finalized at land (candidate a), with branch-tip
scanning and content-nonce tiebreak folded in as design elements rather than
separate mechanisms -- see docs/modules/tickets.md#decision-record-t-0162
for the full comparison and why TICK001/TICK002 are unwaivable.

Evidence: 7 tests in tests/test_tickets_collision.py (see evidence list above),
covering: post-archive reissue (incident 1), two-worktree concurrent filing +
real git merge + finalize (incident 2), renumber_one at ~100-reference scale
+ dry-run (incident 3), and TICK002 gate loud-fail/unwaivable-ness.
Also verified: full tests/test_tickets.py, test_tickets_evidence_cli.py,
unit/test_ticket_store.py, system/test_cli_ticket.py,
system/test_cli_ticket_worktree_root.py all still pass; full `make coverage`
suite passes; `frob sys audit` stays PROVED.

Filed: none (no out-of-scope work found; the __main__.py CLI wiring was
brought into scope on tickets.md itself rather than filed separately, since
it is required by this ticket's own `frob ticket renumber <old> <new>`
deliverable, not incidental discovery).

Gates: `frob check --ticket T-0162` clean (0 gate violations, ruff/ty/exports/
frob-arch all pass) after `make coverage`. TICK001/TICK002 gate rules added
and verified against both a stray draft id (fails loudly, TICK002) and a
clean queue (no violation). Not out of scope: T-0176 (`frob ticket land`)
remains queued and unimplemented, as directed -- `finalize_draft` is the
callable API it will invoke.
