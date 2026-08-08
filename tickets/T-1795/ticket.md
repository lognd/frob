---
id: T-1795
title: Advisory-visible land lock (retire pgrep polling; fix DirtyMain misattribution)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Merges T-draft-736f2d46's original ask (requirement 4 from T-1779: an
advisory-visible land lock, not discoverable only by `pgrep`) with two
concrete pieces of live evidence that make it a confirmed bug, not a
nice-to-have.

REQUIREMENT (unchanged from T-draft-736f2d46): a `frob doctor`-style
line, or a marker file, that names which ticket is landing and whether
the lock is CURRENTLY held -- readable without `pgrep`, without any
side effects, and without racing the same self-matching hazard below.

EVIDENCE 1 -- DirtyMain misattributes the owner of staged dirt. T-1222's
detached post-land sweep child failed to commit its own write to
`rapid-debt.jsonl`, leaving it STAGED in root. `describe_root_dirt`'s
T-1740 callout named T-1699/T-1755 as the likely author -- it GUESSED
from the file's usual owner (`_SWEEP_OWNED_DIRTY_PATHS`'s membership
test), not from who actually staged it. Three separate agents hit this
DirtyMain refusal, all three read the wrong ticket id in the message,
and none could diagnose the real cause from the refusal alone. Fix:
attribution must be SYMBOLIC (which process/commit staged this content
-- `git log`/reflog on the staged blob, or a marker the sweep child
itself writes naming its own ticket id before staging) and must say
"unattributed" when it cannot be determined, never a plausible-but-wrong
ticket id. Same "cannot verify is never verified" rule the sweep already
claims to follow elsewhere (T-1779's own docs section quotes this
exact rule for `_probe_worktree_liveness`'s ambiguous case) -- this is
the same rule applied to a message body, not just a return value.

EVIDENCE 2 -- `pgrep -f "frob ticket land"` (or any `until ! pgrep -f
"frob ticket land T-XXXX"` polling loop) is not a reliable land
detector and can hang forever on itself. A shell running exactly that
loop (`until ! ps aux | grep "ticket land" | grep -v grep`) matched its
OWN command line -- the loop's own argv contains the literal string
"ticket land T-XXXX" -- so the poller never saw an empty result even
after the real land process had long since exited. Found live: a shell
stuck 19 minutes in this exact loop, killed by the coordinator. This
polling recipe was recommended THIS SESSION (the playbook's own worked
example, `ps aux | grep "ticket land" | grep -v grep`) -- it needs
either a fix (a `grep -v` for the poller's own pid/pattern, fragile) or,
better, retirement in favor of reading the SAME advisory surface this
ticket is asking for (a lock file/doctor line a coordinator can read
once, no polling loop needed at all -- the self-matching hazard cannot
exist for a single stat/read).

Both pieces of evidence point at the same fix: make the land lock's
state a first-class, directly-readable fact (file existence + holder
metadata, or a `frob doctor` line), so neither "who staged this" nor
"is a land still running" ever again depends on grep pattern-matching a
process table that can match the watcher itself.
