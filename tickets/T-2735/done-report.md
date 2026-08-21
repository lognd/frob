## Done report

Changed:
- docs/modules/app.md#waive-audit-t-2467 (waive-audit watermark bullet)

Documented T-2721's git-tracked/mirrored waive-audit watermark, which the
section previously described as living at `.frob/waive-audit-
watermark.json` (stale -- pre-T-2721 location). This section was blocked
by T-2694's live cross-worktree lease for T-2721's entire duration, so
T-2721 could not update it and waived AFFECT001 on `save_watermark`
citing this ticket as the follow-up (T-2694 has since landed, freeing the
lease).

Content added: the watermark now lives at the repo ROOT
(`waive-audit-watermark.json`, `.gitignore`-negated like
`rapid-debt.jsonl`), is git-tracked (not `.frob/` scratch), and
`save_watermark` commits it in `root` AND mirrors-and-commits it onto the
primary checkout immediately when `root` is a worktree (same shape as
T-2563's ledger mirror), since `waive-audit` is `NOT_TICKET_SCOPED` and
would otherwise never reach main until its worktree's ticket landed.
Made the WHY explicit and load-bearing, not just the WHAT: T-1614's first
live pass classified 100 waiver directives inside a disposable worktree;
the primary checkout's own copy was simply ABSENT afterward, `waive-audit
scan` reported `not_covered=967` before the worktree's file was copied
across by hand and `not_covered=867` after -- proof the 100
classifications were genuinely gone from everywhere the fleet looks, and
silently so. Added an explicit "do not clean this up back into `.frob/`
or `.gitignore`" line so a future pass does not reintroduce that failure
mode believing the root-level file is stray clutter.

Every ticket id cited in the new prose (T-1614, T-2467, T-2485, T-2563,
T-2721) verified to resolve under tickets/ before closing.

Evidence: doc-only chore, no code/test surface changed -- cmd: evidence
channel used (docs-kind ticket, T-0215).

Filed: none.

Gates: `frob check --ticket T-2735` -- SCOPE/DOC/COV clean for this
ticket's touched set (docs/modules/app.md only); the one remaining
PRE001 (stale pre-work sweep) cleared via `frob ticket sweep T-2735`
before closing.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 17 error(s), 894 warning(s), 707 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
