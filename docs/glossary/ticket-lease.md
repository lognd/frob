# Ticket lease

A ticket lease is the write claim a holder takes on a ticket's `scope`
globs when work starts (`frob work`, `frob ticket start`). While the
lease is live, no other holder can claim overlapping paths; a second
caller gets `E-LEASE-HELD`. It exists so parallel agents and humans do
not edit the same files.

Where it lives: one TOML file per ticket at
`<common_dir>/frob/leases/<id>.toml`, shared by every worktree of the
clone. Acquisition is atomic under a single lock file.

Lifecycle, as exposed by `frob lease --help`:

- `frob lease list` shows the live leases of this clone; `--contention`
  adds files claimed by more than one lease.
- `frob lease widen <ticket> [--glob G]` re-reads the ticket scope
  (optionally adding globs) and rescopes your lease to match. Use it
  when a check reports SCOPE001.
- `frob lease release <ticket>` gives up your lease on a finished but
  unlanded ticket; the ticket stays in-progress and `frob land`
  re-takes the lease.
- `frob lease rekind <ticket> [--agent LABEL]` re-claims the lease as a
  human (or as the labelled agent), switching its idle window.
- `frob requeue <ticket>` releases the lease and returns the ticket to
  the queue.

See also: [ticket design](../design/frob/tickets.md).
