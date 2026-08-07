## Done report
Investigated: the FROBLEM's premise is now stale. `attr flag=<id>` IS a real,
implemented LINT004 discharge -- `_lint.py::check_lint_kill_switch` clears a
node when `node_flag_ids(node)` is non-empty, the strata grammar parses the
generic `attr flag=<id>;` node property, and it is documented at
docs/strata/threat.md:349 ("declare `attr flag=<id>;` naming the real
kill-switch") with the `waive` alternative explained at 389-394 (used when no
real kill-switch exists yet). The docs post-date the 2026-07-18 FROBLEM. So
the message was not wrong -- but its residual, valid concern (a repo without a
kill-switch yet was misled toward the flag-only remedy) is addressed: the
LINT004 detail now names BOTH escapes (`attr flag=<id>` OR `waive "LINT004"
... ticket ...`). Evidence test asserts the detail contains both. No grammar/
check change needed.
