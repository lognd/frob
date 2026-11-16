# Cycle

Status: current
Owner: frob
Decisions: none
Audience: user

A cycle is a fixed, dated window of planned work (a sprint). It has a
start day, an end day, a goal, a set of member tickets, and, once
closed, a completion ratio and a retro. Work needs a live cycle:
`frob work` and `frob land` run against the open cycle that contains
today.

Create one with `frob cycle new --start YYYY-MM-DD --goal TEXT`. The
end day defaults to start plus the configured `[pm] cycle_days` minus
one; pass `--end YYYY-MM-DD` to override. An identical repeat returns
`already`; an overlapping or different cycle is refused.

Fill it with:

- `frob cycle assign <ticket>` adds a ticket (default: the open cycle
  containing today, else the next planned one); it is refused past
  capacity unless over-committed.
- `frob cycle plan` proposes a fill from ready work in rank order,
  preferring the next milestone and never going past capacity;
  `--apply` performs the assignments.
- `frob cycle unassign <ticket>` removes a ticket (idempotent).

Inspect with `frob cycle show` (default: the current cycle) and
`frob cycle list`.

Close one with `frob cycle close <cycle>`, where the cycle is a ULID,
a `~handle` or a `START..END` alias. Closing carries incomplete work
to the next cycle and records the ratio and retro. It is refused
while live work is still in progress, so land or `frob requeue` those
tickets first.

See also: [ticket lease](ticket-lease.md).
