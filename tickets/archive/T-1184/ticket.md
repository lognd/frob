---
id: T-1184
title: 'land: _do_wip_commit''s negated :!.frob pathspec aborts git add outright on
  git 2.34.1'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: COV002/SCOPE002 need the new fallback tests bound to T-1184's own file
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface (SYS104) had to add TestWipAddIgnoredPathFallback to
    the testsuite interface node
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_gitignored_frob_falls_back_and_still_lands
- tests/test_ticket_land.py::TestWipAddIgnoredPathFallback::test_is_ignored_path_refusal_matches_gits_fixed_message
designated_repro_test: null
threat: null
component: null
---
_do_wip_commit's git add invocation (src/frob/tickets/_land.py:1854,
`git add -A -- . :!.frob`) fails outright on this environment's git
(2.34.1): naming `.frob` in a NEGATED pathspec still trips git's
"explicitly named ignored path" refusal (exit 1, "The following paths
are ignored by one of your .gitignore files: .frob"), aborting the ENTIRE
add -- not just skipping `.frob`. Reproduced directly against a clean
main checkout with zero ticket-related changes staged, so this is not
specific to any in-flight ticket's diff.

`.frob/` is already covered by the repo's own top-level .gitignore
(T-1006's own stated rationale for the negated pathspec was defense for a
bare test fixture that has NOT gitignored .frob/) -- for this repo,
`git add -A -- .` alone (no negation) already excludes `.frob/` correctly
and exits 0. The negated pathspec is redundant belt-and-suspenders for the
real repo and is the literal cause of every land's wip-commit step
failing outright in this git version.

Blocks EVERY `frob ticket land` in this environment -- found while
landing T-1179 (unrelated to that ticket's own acceptance criteria) and
fixed inline there only because it structurally blocked completing that
land; filing this ticket to track the fix on its own record and note any
test-fixture-repo defense-in-depth this drops (T-1006's original bare-
fixture case, if any test exercises a non-gitignored .frob/ specifically).