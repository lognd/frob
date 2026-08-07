## Done report

renumber_one already rewrites STRUCTURAL id references (a ticket's own id,
blocked_by/parent, frob:* directive lines in code) when finalizing a
draft, but never touches free-text Done-report prose (a "Filed: T-draft-
<hex8> (...)" claim about a sibling draft) since that is not a structural
field. _land_finalize_and_close now collects the exact old-draft-id ->
final-id mapping renumber_one/finalize_draft already compute -- both for
the ticket being landed itself (if it started as a draft) and for every
sibling draft _finalize_sibling_drafts finalizes alongside it (changed
that helper's return type from a bare tuple of new ids to an old->new
dict so the mapping survives) -- then runs a new
_rewrite_draft_references_in_bodies(worktree, mapping) pass BEFORE
_commit_finalize_writes: it loads both the active and archive ledgers
(load_all/load_archive), regex-substitutes every occurrence of an old
draft id in each ticket's body text with its final id (a fixed-width
T-draft-<hex8> token has no partial-match risk; a trailing
(?![0-9a-fA-F]) guard is kept anyway as a structural safety margin), and
writes back only the stores that actually changed (write_all/
write_archive), so the rewrite lands in the SAME finalize commit as the
structural renumbering. This closes the recurring TICK006 phantom-filing-
claim false-positive (T-0778/T-0797, T-0745/T-0764) without touching
renumber_one itself, staying inside the ticket's _land.py-only scope.

Regression test (TestDraftReferenceRewriteOnLand): lands a worktree whose
own Done report cites its own pre-finalize draft id ("Filed: T-draft-...");
asserts the landed ticket's final id is not the draft id, the draft id
string is gone from the final ticket's body, "Filed: <final_id>" is
present instead, and zero "T-draft-" substrings survive anywhere in
main's landed tickets.md.

Gates: frob check --ticket T-0811 clean (0 errors, gate-summary pass).
frob test --base main PASS. tests/test_ticket_land.py: 77 passed
(includes the 76 pre-existing tests plus the new regression test).

Filed: none.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a32451bda533ca284

Deviations: none from the ticket's plan.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
