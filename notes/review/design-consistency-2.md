# Design consistency pass 2 (D85)

Ticket ~FDTYYEE. The milestone-2 planner (2026-10-04) listed fifteen
contradictions or gaps across the design set while decomposing D76 and
D78-D84 into tickets. Each is resolved below; the design text named in
the last column now states the resolution.

| # | Item | Resolution | Stated in |
|---|---|---|---|
| 1 | plan cache inside the work tree (plugins.md) versus outside (security.md) | outside, under `$XDG_CACHE_HOME/grimble/plans/`, keyed by tree digest and engine, MAC'd | plugins.md 6.1 |
| 2 | findings cache in `.frob/cache.sqlite` (D30, D38) versus security.md 2.2 | executable artifacts leave the work tree; parse and findings caches stay per worktree for the 2 s budget, every row MAC'd and engine-scoped; tracked-state guard and CI ignoring in-tree caches stay | security.md 2.2 |
| 3 | two meanings of "pack" | a pack is the plugins.md directory; packs.md's TOML document is its tier-1 data file; semantic digests for drift, tree digest for trust | packs.md 1.1 |
| 4 | crates the designs never named | `gob-plan` for all of GRL; `packs/std/<family>/*.grl` and generated `gob-std`; rule verbs as a gob-plan module registered per product; `gob-wasm::worker`; `gob-fix` (boundaries.md); ticket-branch generators in frob-ledger | plugins.md 10 |
| 5 | GRL rewrites of TODO001 and others versus the tier-0 Rust rules | the rewrites are unregistered acceptance fixtures until a family moves; the move replaces the Rust rules in one ticket | plugins.md 10 |
| 6 | no migration of an existing ledger to the ticket branch | `frob tickets migrate --to-branch`: build, verify folds, commit, one revertible code commit | navigation.md 2.3 |
| 7 | GATE001 cleared by a "reviewer label" that exists nowhere | removed; only an exception with a ticket clears it | security.md 2.7 |
| 8 | how base findings for no-new-unknowns are computed | from git objects for changed files and P+ rules only, cached by (base commit, engine) | security.md 2.7 |
| 9 | which lock holds process-pack digests | the lock of the product declaring the stage | security.md 2.4 |
| 10 | the CI trust rule had no id | CI016 | cicd.md, security.md 2.11 |
| 11 | PM031 and PM032 have no crate | `frob-pm`, already in boundaries.md; the planner missed it | boundaries.md |
| 12 | storage of the newcomer teaching counter | `.frob/seen.toml`; std rules only | navigation.md 4.1 |
| 13 | no `test` ticket type | kept: test work is a `task` with the label `kind:test`; a new type would add a second way to say the same thing | (no change) |
| 14 | the GitHub autolink limits are unverified | verified by the mirror init ticket against the live API | navigation.md 1 (unchanged) |
| 15 | kernel `replaces` can never run in CI | intended and now stated | security.md 2.9 |
