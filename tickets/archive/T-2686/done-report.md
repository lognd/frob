## Done report

Per-ticket disposition (all 6 re-measured against the current tree, 2026-08-21,
before touching anything):

1. T-1397 -- ALREADY RESOLVED, no action taken. Its third evidence citation
   (`test_rc_file_target_is_shared_not_duplicated`, previously "deliberately
   left unrepointed" per the T-2366 note) was already dropped from the
   evidence list by T-2743 (commit 641ad37e9, 2026-08-20), which established
   the precedent this ticket follows for the two cases below: a direct edit
   to the archived ticket's evidence list, with the disposition reasoning
   already recorded in the ticket body/evidence_changes trail. Current
   evidence list has 2 entries, both resolve. COV003 clean.

2. T-1526 -- ALREADY RESOLVED, no action taken. Same T-2366/T-2743 lineage
   as T-1397. Current evidence list resolves cleanly against
   tests/test_coverage.py.

3. T-1688 -- LIVE, fixed here. Investigated (T-2669 triage, already recorded
   in the ticket body): the cited test asserted "new findings never advance
   the watermark"; T-2324 deliberately REPLACED that invariant (findings
   attributed to an owning ticket now DO advance the watermark, to avoid
   unbounded backlog drift). The successor test proves the opposite claim,
   so rebinding would misrepresent this ticket as still proving an invariant
   it no longer does. No `frob:waive COV003` mechanism exists for this
   finding -- `frob.graph.dsl._MD_WAIVE_HONORED_RULES` (the markdown-waiver
   allowlist) does not include COV003, so a directive in ticket prose would
   be a silent no-op (DSL001 unhandled-directive territory), not a real
   suppression. Followed the T-2743 precedent instead: removed the stale
   node id from `tickets/archive/T-1688/ticket.md`'s `evidence:` list. The
   ticket's remaining 56 evidence ids are untouched and still resolve.

4. T-2344 -- ALREADY RESOLVED, no action taken. `evidence_changes` already
   shows a same-day (2026-08-19) rebind to
   `test_supplychain_lexcheck001_backlog_is_empty_t2469`, a genuine rename-
   chain successor (T-2466 renamed once, T-2469 renamed again after fixing
   the backlog) proving the identical claim. Confirmed the successor exists
   and collects. COV003 clean.

5. T-2348 -- ALREADY RESOLVED, no action taken. Cites the same node id as
   T-2344 and was rebound by the identical T-2344 fix (both tickets shared
   one stale citation to the deleted `TestLexcheck001` method). COV003
   clean.

6. T-2365 -- LIVE, fixed here. Investigated (T-2669 triage, already
   recorded in the ticket body): the cited test asserted "TypeScript
   import_graph is a reasoned, disclosed gap" (KNOWN_GAP, tracked by
   T-2408). T-2408 (done) shipped the missing import-graph walkers, so the
   successor test (`test_typescript_import_graph_is_implemented`) proves
   the OPPOSITE of the original claim -- the gap closed, it was not
   renamed. Same non-mechanism situation as T-1688 (COV003 is not in
   `_MD_WAIVE_HONORED_RULES`). Removed the stale node id from
   `tickets/T-2365/ticket.md`'s `evidence:` list, same T-2743 precedent.
   14 remaining evidence ids untouched and still resolve.

Root-cause note for the record: COV003 cannot be waived via a ticket-body
`frob:waive COV003 reason="..."` directive today -- `_MD_WAIVE_HONORED_RULES`
in `src/frob/graph/dsl.py` only honors REF001/REF002/DOC004/DOC006/INV003/
INV004/BUG002 out of markdown text. This was checked directly (not assumed)
before choosing the evidence-list-edit disposition for cases 3 and 6. Did
not touch `_MD_WAIVE_HONORED_RULES` itself (out of this ticket's scope and
not needed -- the T-2743 evidence-removal precedent already covers this
disposition without a new mechanism).

Proof, both directions:
- Broken-thing-now-works: `frob check --only coverage` (repo-wide, not
  ticket-scoped) reported ZERO COV003 findings after the two edits, versus
  2 before (T-1688, T-2365) -- captured in /tmp/cov_all.out during the
  session.
- Working-thing-still-works: `uv run pytest -q tests/unit/verify/test_worker.py
  tests/test_lang_support.py` -- 50 collected, 0 failed, exitstatus=0 (both
  files' remaining evidence node ids collect and pass); the other 4
  tickets' evidence was independently re-verified as already resolving via
  the same full `--only coverage` run, so no case was assumed clean without
  measurement.

Filed: none. No out-of-scope work found; the removal-precedent
(T-2743) was already established, no new mechanism needed.

Gates: `frob check --ticket T-2686` -- gate:SCOPE/PREWORK clean, no
COV003 anywhere in the repo-wide coverage scan. Every other FAIL in that
run (DRIFT/PERF/REG/SEC/SYS/TEST/TICK/gate:COV's remaining COV001) is
repo-wide pre-existing debt untouched by this ticket's 2-line diff (only
`tickets/archive/T-1688/ticket.md` and `tickets/T-2365/ticket.md` touched).

### Changed
```
 tickets/T-2686/ticket.md | 8 +++++++-
 1 file changed, 7 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_clean_run_advances_watermark_and_compacts_queue` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_real_registry_has_no_conformance_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 16 error(s), 843 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
