# Tier-A auto-fix notes pending a docs/modules/gates.md fold-in (T-1547/T-1548)

This page holds the writeups for Tier-A `--fix` handlers landed while
`docs/modules/gates.md` -- home to every OTHER handler's own writeup, in
its "`--fix` Tier-A deterministic auto-fix handlers" section -- sat under
an in-progress lease (T-1205). Each section below names its own follow-up
ticket to fold it into `gates.md` proper once that lease clears; see each
section's own disclosed-scope note.

<!-- frob:describes src/frob/gates/_fix_engine.py::fix_e501_merge_introduced -->
<!-- frob:describes src/frob/gates/_fix_engine.py::_merge_touched_python_files -->
<!-- frob:describes src/frob/gates/_fix_engine.py::_e501_lines_for_file -->
<!-- frob:describes src/frob/gates/_fix_engine.py::fix_cov002_ticket_directive_insertion -->
<!-- frob:describes src/frob/gates/_fix_engine.py::_insert_ticket_directive_above -->

## `fix_e501_merge_introduced` auto-fix

`fix_e501_merge_introduced` (in `src/frob/gates/_fix_engine.py`, registered
in `TIER_A_HANDLERS["E501"]`) closes the E501 item T-1531's own deferral
list named: an over-long line a land-time MERGE introduces (as opposed to
a pre-existing E501 finding anywhere else in the repo) gets a targeted
`ruff format` pass, scoped to exactly the `.py` files that merge touched
-- never a whole-tree `ruff format` sweep, which would re-litigate every
unrelated pre-existing E501 finding in the repo.

`_merge_touched_python_files` derives the touched set from `HEAD`'s own
two-parent merge diff (`git diff --name-only HEAD^1 HEAD^2`) when `HEAD`
is a real merge commit, or from uncommitted working-tree changes against
`HEAD` (`git diff --name-only HEAD`) for the in-progress-merge shape
`frob ticket land`'s own pre-land Tier-A phase runs in (the worktree has
already `git merge main`d but not yet committed that merge). Distinct
from `fix_fmt001_directive_wrap`, which only ever rewraps `frob:`-
directive comment lines, never ordinary code.

`_e501_lines_for_file` re-verifies E501 is actually gone (a scoped `ruff
check --select E501 --output-format json` before and after the targeted
format pass) before counting a file as fixed -- `ruff format` cannot
always shorten every over-long line (an unbreakable string literal, for
instance), so a file whose E501 lines survive the format pass is left as
an ordinary, still-live E501 finding rather than misreported as fixed.

**Disclosed scope note (2026-08-05):** this note lives in its own file
rather than folded into `docs/modules/gates.md`'s own "`--fix` Tier-A
deterministic auto-fix handlers" section (where every sibling handler's
own writeup lives) because `docs/modules/gates.md` was under an
in-progress lease held by a concurrent ticket (T-1205) at the time this
ticket landed -- editing it here would have collided with that ticket's
own in-flight edits (playbook's ScopeLeaseConflict guidance: skip the
edge, do not requeue anyone, disclose it instead). A follow-up ticket
should fold this section into `docs/modules/gates.md` proper once T-1205
lands and the lease clears -- filed as T-draft-ad6cd565 (renumbers to a
real id at land).

## `fix_cov002_ticket_directive_insertion` auto-fix (T-1548)

`fix_cov002_ticket_directive_insertion` (registered in
`TIER_A_HANDLERS["COV002"]`) closes a COV002 finding (a changed symbol
with no `frob:ticket` edge to an open ticket and no covering ticket
scope) by inserting `# frob:ticket <landing-id>` (or `//` for a `.rs`
source) directly above the symbol -- but ONLY when the caller supplies a
real, currently OPEN `ticket_id` (the landing ticket, `None` outside a
land context: this handler is a whole no-op then, per Tier-A's own
never-guess posture) and the finding is against `working_diff(root,
"main")` -- this land's own diff, the only diff this handler has any
basis to attribute a fix to.

This is the one Tier-A handler in this module whose fix genuinely depends
on WHICH ticket is running the fix pass, which no other handler here
needs -- `TIER_A_HANDLERS`' callable shape and `apply_tier_a_fixes`'s own
signature both grew a `ticket_id: str | None` parameter for it (T-1548);
every other handler ignores the new argument, unchanged behavior.

**Disclosed scope note (2026-08-05):** same lease situation as the E501
section above (T-1205 held `docs/modules/gates.md`) -- filed as
T-draft-ad6cd565 (the same follow-up ticket the E501 section above
names; both sections fold into `gates.md` together once the lease
clears).
