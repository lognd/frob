## Addendum (the defect demonstrating itself)

Self-referential confirmation, live: this ticket was itself filed and
promoted (`T-draft-f4642a56` -> `T-2197`) inside the `t-2188` worktree,
and stayed invisible on main -- `ls tickets/T-draft-f4642a56` on main
found nothing; the coordinator's own check reported `found on branch:
t-2188` -- for the entire span between filing and this land. The ticket
documenting "a worktree-local promote is invisible to everyone else
until landed" was, for that span, itself exactly that. Not a
contrived reproduction; the first real instance was this ticket.

Two concrete incidents fold in here, both from the SAME root cause and
worth citing together:

1. **Every downstream step succeeds silently, with no cross-check.**
   T-2188 (worktree-local) ran `frob ticket block T-2188 --by T-2195`
   against a T-2195 that existed ONLY on T-2188's own branch -- the
   `block` command itself has no way to know the target id is
   unreachable from main, so it succeeded and printed a normal
   confirmation. T-2188 then landed carrying `blocked_by: [T-2195]`
   while T-2195 was still worktree-only. A fresh agent dispatched to
   work T-2195 correctly refused with `no ticket T-2195` -- the ONLY
   place in the whole chain that caught the gap, and only because that
   agent's own ticket-resolution path happens to check existence
   strictly. Every ticket-CLI step up to that point -- `promote`,
   `block`, `attach` (addenda), `priority` -- reported success and was
   indistinguishable from operating against a real, landed id.

2. **The pre-dispatch check MEASURED the gap and then discarded it.**
   `scripts/fleet_status.py --ticket T-2195`, run by the coordinator
   before dispatch, printed `main: ticket does not exist on main` on
   one line and `dispatchable: True` on the next -- the fact was
   computed and displayed, then not consulted by the verdict line
   immediately below it. This is filed separately as **T-2196** (same
   root shape, different repair surface: `fleet_status.py`'s own
   verdict logic vs. this ticket's ticket-CLI/ledger-resolution scope)
   -- the two tickets should cross-reference each other's fix, since a
   complete repair needs both: the ticket layer should make an
   unreachable-from-main id loudly distinguishable (this ticket's own
   WANTED list), AND any pre-dispatch check consuming that signal
   needs to actually gate its verdict on it, not just print it
   (T-2196's own scope).

Both incidents are the SAME underlying failure -- a worktree-local
ledger mutation that looks, at every individual step, identical to a
real one -- surfacing at two different layers (the ticket CLI itself,
and a consumer script built on top of it). Fixing only one layer
leaves the other's blind spot; both should land before this class of
handoff failure is considered closed.
