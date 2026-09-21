"""frob.worktrees -- disposable (non-ticket) worktree lifecycle helpers.

T-4437 (F-055 class): `frob doctor`/`frob clean` never accounted for the
short-lived `git worktree add` scratch dirs the BUG002 repro pipeline
(`frob.gates._bug_repro`) and the land-squash pipeline
(`frob.tickets._land_compose`) each cut under `/tmp` -- both are cleaned up
in a `finally`/context-manager on the HAPPY path, but a killed land or a
killed check run bypasses that cleanup entirely (SIGKILL runs no Python
cleanup code), leaking `git worktree add`-registered entries that neither
tool ever sweeps. This package is the sweep: `_disposable_sweep` finds
them, decides liveness from a creator-stamped pid file, and removes the
dead ones with `git worktree remove --force` + `git worktree prune`."""

from __future__ import annotations
