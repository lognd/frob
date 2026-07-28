# ESTATE migration: precise capability spellings across the sibling estate

T-1071, closing the "ESTATE" follow-up named in T-0717's mandate point 3
and re-confirmed by T-0771's Done report once `net` got a real
connect/listen needle split. This is the per-repo recipe an agent (or a
human) follows to move one sibling repo's `.strata` `may` declarations
from a coarse/legacy spelling to the precise `family.mode` vocabulary
(`src/frob/vet/_capability_modes.py`), and the record of what this repo
did on 2026-07-28 to kick that off across the fleet.

This repo (`frob`) cannot edit sibling repos directly -- worktree agents
here have no write access outside this clone's own tree. The deliverable
from this ticket is entirely FROB-SIDE: the routed tickets landed via the
existing `frob fleet route` machinery (T-0573), which writes straight
into the target repo's own ledger, plus this recipe so whichever agent
picks up each routed ticket does the actual `.strata` edit consistently.

## Why this migration exists

`FAMILY_MODES` (`src/frob/vet/_capability_modes.py`) defines the
canonical mode set per capability family. A bare family name (`may
"net"`, `may "fs"`) stays legal forever and is interpreted fail-closed as
the union of that family's modes -- nothing here makes coarse
declarations wrong. But where a node's REAL behavior only ever exercises
one mode (a client that only connects out, never listens; code that only
reads a file, never writes it), spelling that precisely
(`may "net.connect"`, `may "fs.read"`) is REWARDED: SYS101 discharges a
narrower, more honest obligation and fails conformance the instant an
unexpected mode (a write, a listen) is observed. The legacy hyphenated
spellings (`fs-write`, `fs-read`) are SCANNER kinds, not `may` spellings,
and are a separate, already-tracked deprecation (`LEGACY_CAPABILITY_ALIASES`,
sunset 2026-10-20) -- a `.strata` file that still writes `may "fs-write"`
verbatim (rather than the scanner internally producing that kind) should
also be caught and fixed by this same pass if found.

## Per-repo recipe

1. `grep -n 'may "net"\|may "fs-write"\|may "fs-read"' design/*.strata`
   in the sibling repo's own tree to find every coarse/legacy `net`/`fs`
   declaration.
2. For each hit, read the surrounding node's actual behavior (the comment
   immediately above the `may` line in this repo's own `.strata` files
   already documents which concrete client/behavior backs the
   declaration -- follow the same convention in the sibling).
   - If the node only ever connects outbound (an HTTP client, a registry
     fetch, ...) and never accepts inbound connections, narrow to
     `may "net.connect"`.
   - If the node only ever listens/accepts (a server bind), narrow to
     `may "net.listen"`.
   - If the node genuinely does both (e.g. a peer that both dials out and
     accepts), leave it as the coarse `may "net"` -- do not force a split
     that misrepresents real behavior; coarse is always legal.
   - Apply the same read/write logic for any literal `fs-write`/
     `fs-read` `may` spellings, replacing with `may "fs.write"` /
     `may "fs.read"` (or leaving bare `may "fs"` if the node genuinely
     does both).
3. Re-run that repo's own `frob check --only sys` (SYS100/SYS101) to
   confirm the narrowed declaration still discharges cleanly against
   observed effects -- a narrowing that does NOT discharge means the
   behavior read in step 2 was wrong, not that the gate is wrong.
4. Commit with a message naming the ticket this recipe was routed under
   (see below), no separate write-up needed beyond the routed ticket's
   own Done report.

## 2026-07-28 fleet sweep (T-1071)

Every sibling in `fleet.toml` was greped for `may "net"` and literal
`may "fs-write"`/`may "fs-read"` in `design/*.strata`. Three repos
(`feldspar`, `typani`, `lograder`) have no `net` capability at all and no
literal legacy `fs-*` spelling -- nothing to route, left untouched. The
other five had real hits and got a routed ticket each via
`frob fleet route` (T-0573), landing directly in that repo's own
`tickets.md`, scoped to `design/*.strata` only, kind `docs` (a spelling
change, not new capability), body pointing back at this guide:

| Sibling | Routed ticket (filed 2026-07-28, kind `docs`, scope `design/*.strata`) | Hits found |
|---|---|---|
| lithos | T-0076 | `may "net"` (registry-fetch client, `design/lithos.strata`) |
| graphite | T-0024 | `may "net"`, `may "fs-read"` (x2), `design/graphite.strata` |
| aprog-public | T-0062 | `may "net"` (x3), `design/aprog-public.strata` |
| aprog-private | T-0017 | `may "net"` (x2), `design/aprog-private.strata` |
| logand.app | T-0007 | `may "net"` (x3), `design/logand-app.strata` |

Ticket ids are as returned by `frob fleet route` (`fleet: routed T-XXXX
into <repo>`) at call time -- they are that sibling's own ids, in that
sibling's own numbering space, unrelated to this repo's own ticket ids.
Each sibling's own `tickets.md` is the source of truth for the ticket's
current state going forward; this table is a point-in-time record of
what was routed and why, not a live status mirror.

## Not done here (explicitly deferred, not silently dropped)

`env`/`proc`/`ffi` tier-2 joins and their own future ESTATE sweeps are
out of scope for T-1071 (T-0771 Done report already tracks `proc`/`ffi`
as unwired; `env` got its own tier-2 join in T-1075 but no fleet sweep
has been run for it yet). A follow-up ticket for an `env`-precise fleet
sweep, once someone decides it is worth a second pass rather than folding
into whichever ticket eventually wires `proc`/`ffi`, is not filed by this
ticket -- noting it here so it is not forgotten, per this repo's own
TODO-tracking discipline.
