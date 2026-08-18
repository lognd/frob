# T-2350 diagnosis: timing/visibility race, NOT an identity-matching bug

## Answer to the coordinator's question

TIMING/VISIBILITY RACE. Confirmed by reading the actual code path (not
guessed): the TICK006 phantom-citation auto-filer's identity-matching
logic itself is straightforward and correct --
`fix_tick006_phantom_refile` (src/frob/gates/_fix_engine.py:331) builds
`known_ids = set(queue.tickets) | set(archived.danger_ok)` and checks
simple string membership. There is no fuzzy matching, no normalization
step, nothing that could misidentify a real, well-formed ticket id as
unknown -- if `queue`/`archived` genuinely contained T-2345 at the
moment this ran, it would have matched. The two false positives (T-2343
citing a deleted stray draft, T-2349 citing T-2345, which was real and
committed well before land ran) both show the SAME shape: a real id that
existed on disk, at the shared root, before land started, that the
Tier-A check somehow did not see.

## What I traced, in-scope (read-only; no edits made -- see below)

- `fix_tick006_phantom_refile(root, queue)` receives `queue` as a
  parameter, does NOT reload it itself -- only `archived` is loaded
  fresh inside this function (`load_archive(root)`).
- Its only caller is `_land_cmd.py::_apply_root_tier_a_fixes(root,
  ticket_id)`, which DOES call `load_active(root)` fresh, immediately
  before invoking the Tier-A dispatch table. This looked, on first
  read, like it should always see current disk state.
- `load_active` -> `load_all` -> `_read_index_cache`
  (src/frob/tickets/_store.py:1246): the v2 ticket-index cache's own
  staleness check compares the LIVE glob's exact `(path, mtime_ns)` set
  against the cached entries -- an added ticket file changes the path
  SET, which is checked before mtimes, so a brand-new ticket.md is
  structurally a cache MISS, not a stale hit. Read this code carefully
  looking for the bug and did not find one here -- this mechanism looks
  sound for the simple "a new file appeared" case.

## Where I could not go further

The remaining candidate mechanism -- `root`'s own working tree being
reset/checked-out to an earlier ref at some point in `frob ticket
land`'s multi-step pipeline (merge-worktree-onto-main, the pre-land WIP
snapshot, etc.), such that `_apply_root_tier_a_fixes(root, ...)` runs
against a transient tree state that predates a ticket filed moments
earlier via a SEPARATE `frob ticket new` call to the same shared root --
requires reading `_land_cmd.py`'s full root-sync sequence in detail,
which is under T-2351's live lease (confirmed: `frob ticket scope
T-2350 --add src/frob/gates/_fix_engine.py` ALSO refused, T-2351 holds
both `_fix_engine.py` and `_land_cmd.py`). This is plausibly the SAME
underlying class of defect T-2328/T-2351 already own: a step mid-land
transiently reverts/desyncs `root`'s own working tree, and whatever
reads happen in that window see stale state. I did not force a scope
collision or attempt an edit to find out.

## Recommendation

Do not spin up a separate ticket to chase this further right now --
hand it to whoever owns T-2351, since the mechanism (root tree
transiently inconsistent mid-land) is the same shape, possibly the same
root cause, as what T-2351 is already fixing. If T-2351's fix resolves
root-tree-state consistency during land generally, re-test whether the
TICK006 false-positive pattern also disappears before opening a new
ticket for it specifically.

No code changes made. Ticket left `queued` -- both files a real fix
would plausibly need (`_fix_engine.py`, `_land_cmd.py`) are under
T-2351's live lease.
