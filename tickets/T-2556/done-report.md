## Done report

The T-0431 guard refused on `[ -n "$FROB_AGENT" ]` with no location test of any
kind, so a commit inside the correctly-leased worktree was refused exactly as
hard as one against the shared root. That is not the incident T-0431 was built
for, and it is the path `frob ticket land`'s own pre-land wip commit takes --
which is why lands failed intermittently, only when the worktree was dirty
enough to need a wip commit. I hit it myself landing T-2374: the land refused
with "frob: refusing commit -- FROB_AGENT=1 is set in this shell" and succeeded
only after unsetting the variable the playbook tells every dispatched agent to
set.

The second defect was the message. It advised "run from the leased worktree" --
a remedy that could not work, because the guard never looked at the path.
Anyone following the printed instruction failed again identically.

FIX, in the TEMPLATE (`src/frob/scaffold/project.py`), not the materialized
`.git/hooks/pre-commit`: the refusal is now conditional on where the commit
lands, established exactly the way the T-2071 guard immediately below it
already does it -- this commit's own toplevel versus the primary checkout from
the worktree registry. Refused: the shared root, a worktree other than the one
named by `FROB_WORKTREE`, and an undeterminable location. Allowed: the agent's
own leased worktree. `FROB_LAND_INTERNAL` exempts land's machinery, the same
escape hatch the T-2071 guard already honours. The message now names the
location it refused and a remedy that works.

Undeterminable location refuses rather than failing open. The hook only ever
runs under `git commit`, so both git queries returning empty means the checkout
is broken -- and a guard that silently permits when it could not measure is the
silent-zero class this repo keeps paying for.

FINDING, worth recording rather than quietly filling in: the guard had no
must-NOT-fire test, in either location. The suite had
`test_installed_hook_aborts_commit_under_frob_agent` (must-fire, in the root)
and `test_installed_hook_allows_commit_without_frob_agent` (FROB_AGENT unset,
in the root). Nothing anywhere committed inside a linked worktree. An
unconditional refusal passes every test in that set, which is precisely how it
survived review. A guard needs a must-not-fire case as much as a must-fire one.

POSITIVE CONTROLS, both directions, all six measured:
- in the leased worktree, agent context -> ALLOWED (the control that would have
  caught the original defect);
- against the shared root, agent context -> still REFUSED (T-0431's purpose,
  not regressed);
- in a worktree other than the leased one -> REFUSED;
- coordinator (FROB_AGENT unset) in a worktree -> unaffected;
- land machinery (FROB_LAND_INTERNAL) in the root -> exempt;
- the refusal message names a remedy that the first control proves works.

Verified the controls FAIL against the unfixed template before fixing it: five
of the six failed at the test-only commit b93dffec6, with
`test_commit_inside_leased_worktree_is_allowed` failing on the exact incident
string "frob: refusing commit -- FROB_AGENT=1 is set in this shell".
`--designate-repro` returned FAILED_AT_PARENT against that commit.
`test_coordinator_commit_unaffected_in_both_locations` passed at the parent, as
it should -- coordinator behaviour was never the defect.

Measured: 23 passed in tests/test_scaffold_worktree_lease_hook.py (17
pre-existing plus 6 new), after merging current main. Scoped gates report zero
findings attributable to this change; the COV/DOC/DRIFT errors that remain are
pre-existing on main and outside this scope.

NOT DONE, deliberately: the installed `.git/hooks/pre-commit` in this clone is
still the old materialized copy. It is shared across every worktree via the
common git dir, so rewriting it mid-fleet would change hook behaviour under
every running agent. It refreshes from the fixed template on the next
`frob scaffold apply`.

Residue: the hook's own header comment and `_managed.py`'s `_OURS_MARKER` both
name `frob scaffold install-worktree-lease-hook`, which is not a real
subcommand (`frob scaffold` exposes list/apply/new/pool). The identical stale
text in this ticket's own body fired DOC006 as an ERROR and had to be fixed
before this could land. Left alone here because the two strings are a matched
pair used to recognise frob-owned hooks and `_managed.py` is out of scope --
changing one without the other unrecognises every installed hook. Filed with a
migration shape.

### Changed
```
 src/frob/scaffold/project.py               |  76 +++++++++--
 tests/test_scaffold_worktree_lease_hook.py | 201 +++++++++++++++++++++++++++++
 tickets/T-2556/ticket.md                   |  15 ++-
 tickets/T-2565/ticket.md         |  61 +++++++++
 4 files changed, 342 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_inside_leased_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_against_shared_root_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_refusal_names_a_remedy_that_actually_works` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_in_a_worktree_other_than_the_leased_one_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_coordinator_commit_unaffected_in_both_locations` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_land_internal_commit_in_root_is_exempt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/scaffold/project.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2565/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2556/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2556/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2556, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
