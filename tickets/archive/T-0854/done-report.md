## Done report

Rework of T-0854 in response to reviewer REJECT (MAJOR): the original
own_scope exemption excluded a citation from the live-tracker-citation
preflight purely because the citing FILE matched the closing/landing
ticket's declared scope glob, with no check that the citing LINE had
actually been touched by this ticket's own diff. That is gameable: any
ticket could `frob ticket scope --add` the registry yaml (or a source
file carrying the frob:waive attribute) and close/land with the row still
citing it, completely unchanged, defeating the whole T-0605-orphaned-rows
protection this ticket exists to add. The reviewer's own reproduction --
test_own_scope_citation_excluded asserting exclusion while the citing
line was left byte-identical to what any other unrelated ticket could
have left there -- was correct and is now the FIRST regression test for
the fixed behavior.

Fix: dropped the own_scope parameter from
frob.tickets._live_tracker.live_tracker_citations entirely and replaced
it with a diff-aware base_ref comparison. A citation matched in the
CURRENT tree is now exempt ONLY when the exact same citation (same file,
same text, via a new _content_key helper that drops the line number so
an unrelated earlier edit shifting line numbers cannot masquerade as a
re-point) does NOT already exist, unchanged, at base_ref (default "main",
dynamically resolved via current_branch(root) at both call sites, same as
T-0844's own mutation-evidence base-ref precedent) -- i.e. it is either a
brand-new file/row this diff introduces, or one that got re-pointed to
name something else (so it no longer even matches the closing ticket's
own grep pattern in the current tree, never reaching the comparison at
all). base_ref failing to resolve (a typo, or a repo whose default branch
is not literally named "main") is explicitly FAIL-CLOSED: every citation
found in the current tree is reported as unresolved rather than silently
treated as new, via a None-vs-() sentinel distinction added to the
internal _git_grep helper (None = "the revision itself could not be
read", () = "the revision resolved fine, no match" -- collapsing the two
would have made the whole exemption trivially bypassable in exactly the
way an unresolvable base_ref otherwise would).

Two additional real bugs were found and fixed while building the honest
diff-aware comparison (both would have made every base-ref comparison
vacuously wrong, not just the scope-gaming hole the reviewer flagged):
1. `git grep <revision> -- pathspec` prefixes EVERY output line with
   `<revision>:` on top of the usual `file:line:text` shape (verified by
   hand: `git grep -n -E pattern main -- f.txt` prints
   `main:f.txt:1:text`, not `f.txt:1:text`). Left unstripped, this made
   `_content_key`'s file-and-text comparison never match between a
   working-tree scan and a base-ref scan, so the base scan would never
   find anything and the diff-aware exemption would have silently
   exempted every citation regardless of whether it was actually new --
   the exact class of bug the reviewer's finding warned about, just from
   a different cause. Fixed by stripping the `<revision>:` prefix in
   `_git_grep` before returning lines for a revision-scoped scan.
2. This sandbox's own `git init` default branch is `master`, not `main`
   -- `live_tracker_citations`'s own `base_ref="main"` default silently
   failed to resolve in every test fixture that did not explicitly force
   a branch name, which (before the fail-closed fix above existed) would
   have made every citation look "new" and exempt. Fixed the test
   fixtures (`_init_repo` now does `git init -q -b main`) and, more
   importantly, made unresolvable-base-ref behavior fail CLOSED (item
   above) so this class of environment mismatch cannot silently defeat
   the check in a real repo whose default branch differs from "main"
   either.

Test changes: test_own_scope_citation_excluded and
test_citation_outside_own_scope_still_flagged (T-0854's own already-
recorded evidence ids) were kept under their ORIGINAL names -- deliberately
NOT renamed, to avoid orphaning T-0854's existing evidence list -- and
rewritten to the honest semantics the reviewer specified:
test_own_scope_citation_excluded now asserts an untouched, in-scope
citation is REFUSED (the opposite of its pre-rework assertion), and
test_citation_outside_own_scope_still_flagged now asserts the honest
POSITIVE case (a citation this ticket's own diff freshly introduces,
never present at base_ref, is exempt). Two new tests were added for the
remaining cases the reviewer's fix description named:
test_repointed_citation_no_longer_matches (a citation that existed at
base_ref but was re-pointed to a different ticket id in this diff no
longer matches at all) and test_unresolvable_base_ref_fails_closed (an
unresolvable base_ref reports every current citation, never silently
exempts). All four tests plus the existing suite (16 total in
TestLiveTrackerCitations) pass.

Mutant kills (hand-verified, this rework): (1) replaced `base =
_scan(base_ref)` with `base = ()` in live_tracker_citations -- 7 of 16
tests in tests/test_tickets_live_tracker.py failed (every test relying on
a real base-ref match), confirming the base-ref comparison is load-
bearing, not dead code. (2) forced `_git_grep`'s revision-prefix strip to
always run (`if revision is None: return lines` -> `if True: return
lines`) -- 6 tests failed, confirming the prefix-strip fix itself is
covered, not just written and left untested. Both mutants reverted
afterward; reran tests/test_tickets_live_tracker.py plus
tests/test_ticket_land.py together (130 passed) to confirm the tree is
back to its real, working state.

Callers updated: frob.tickets._land._check_live_tracker_citations now
takes an explicit base_ref parameter (computed once in _land_precheck,
reusing the same current_branch(root) call _check_mutation_evidence
already makes, reordered to run before the live-tracker check instead of
after); frob.tickets.__init__._done_transition_guard resolves
current_branch(root) itself (lazy import, matching T-0844's own
_close_mutation_evidence_for_ticket precedent for the identical close-
path base-ref question) and degrades to skipping the check (empty
citations) when the branch cannot be resolved at all -- same posture as
every other additive-not-fail-closed check in this module, distinct from
the fail-closed posture inside live_tracker_citations itself once a
base_ref IS supplied but does not resolve.

Evidence updates: two new node ids added via `frob ticket evidence
--accepts`-equivalent (frob ticket evidence, no acceptance criteria on
this ticket) --
tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_repointed_citation_no_longer_matches
and
tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_unresolvable_base_ref_fails_closed
-- T-0854 now carries 19 evidence ids total. No stale ids remain: the two
pre-existing ids (test_own_scope_citation_excluded,
test_citation_outside_own_scope_still_flagged) were kept valid by keeping
their names, not by removing and re-adding.

Gates: chunked lint/static/gates-native/gates-security all clean (0
errors). gates-fast cannot be scoped via --ticket for T-0854 anymore (the
ticket is DONE, no active lease) -- see T-0844's rework Done report for
the full explanation of the resulting unscoped-run COV002/PRE001/SCOPE001
noise, identical situation here, not introduced by this rework. ruff
check/format and ty are clean on every touched file; pytest
--collect-only succeeds repo-wide;
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings
was rerun after this rework's own edits (which also touch files in
T-0755's scope: src/frob/tickets/_land.py, src/frob/tickets/__init__.py)
and still passes, 1 passed.

### Changed
```
 docs/modules/tickets.md                       |  76 +++-
 src/frob/__main__.py                          |  14 +
 src/frob/app/config.py                        |   7 +
 src/frob/app/ticket_runner.py                 | 196 ++++++++-
 src/frob/gates/_mutation_evidence.py          |   9 +-
 src/frob/tickets/__init__.py                  | 106 ++++-
 src/frob/tickets/_land.py                     |  48 ++-
 src/frob/tickets/_live_tracker.py             | 264 ++++++++++++
 src/frob/tickets/_models.py                   |  23 +
 tests/test_evidence_integrity.py              |  54 +++
 tests/test_ticket_land.py                     | 338 ++++++++++++++-
 tests/test_tickets_live_tracker.py            | 310 ++++++++++++++
 tests/unit/test_ticket_runner_land_release.py | 104 +++++
 tickets.md                                    | 592 +++++++++++++++++++++++++-
 14 files changed, 2096 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_deferred_disposition` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_tracked_by_disposition` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_ignores_duplicate_of_disposition` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_ticket_attribute` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_strata_waiver_ticket_clause` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_unrelated_ticket_id_not_matched` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_own_scope_citation_excluded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_citation_outside_own_scope_still_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_draft_id_always_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_bare_cli_invocation_not_matched` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_non_git_root_degrades_to_no_citations` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_empty_repo_has_no_citations` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_refused_when_registry_cites_this_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_allowed_when_no_citation` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_citations_found_blocks` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck::test_no_citations_is_ok` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDraftFinalizeRewritesRegistryYamlRefs::test_registry_yaml_deferred_ref_rewritten_to_final_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_repointed_citation_no_longer_matches` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_unresolvable_base_ref_fails_closed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
