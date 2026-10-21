# crunk in CI

Status: current
Owner: crunk
Decisions: none
Audience: contributor

<!-- frob:ticket 01M43ARWT173GKANZ322H41VF1 -->

`.github/workflows/ci.yml` starts with a `changes` job that maps the diff to job sets
(`.github/scripts/plan-jobs.py`, tested by `crates/gob-dev/tests/ci_plan.rs`). The mapping is data in
`crates/gob-dev/changes.toml`, read by both the script and `gob_dev::changes` (`cargo dev changes`,
`cargo dev ci --since <base>`), with one unit test per class. It is a job-level
filter, never a workflow `paths:` filter: a workflow that never starts leaves the commit with no
checks, and a skipped job counts as passing.

| Change | `rust` (whole workspace, Linux and Windows) | `crunk` | `crunk-node` (optional) |
|---|---|---|---|
| only `tickets/`, `changelog.d/`, `notes/`, `docs/design|decisions|migration/` | skipped | skipped | skipped (the `docs-only` job runs fmt, gen check and frob check instead) |
| only `crates/crunk*` or `docs/crunk/` | skipped | runs | when the node runtime changed |
| anything else, including every `crates/gob-*` crate | runs (all three products) | skipped | no |

- The `crunk` job runs rustfmt, clippy, rustdoc and nextest for the crunk packages only (the
  `CRUNK_PACKAGES` list, kept equal to the `crates/crunk*` directories by a test) and the
  one `cargo dev gen all --check`, which covers all three products. frob and grimble tests do not
  run for a crunk-only change.
- The `crunk-node` job runs the node Tailwind runtime tests with `CRUNK_REQUIRE_NODE=1` (a missing
  node fails instead of skipping). It is `continue-on-error`, nothing lists it in `needs`, and it
  must never be a required check, so red or skipped never blocks a merge or the dev channel. The
  playwright gallery tests join it when the gallery port lands.
- The `docs-only` job runs only when every changed path is in a docs class; any other change
  (including a workflow edit, which also sets the `workflows` output) selects the full set.
- An unreadable diff base runs everything.
- A crunk-only push does not refresh the dev channel (the dev jobs wait for `rust`, and a skipped
  job skips its dependants); the next change outside crunk does.
- A frob-only or grimble-only change still runs the whole workspace; scoping the workspace job by
  product needs a package filter in `cargo dev ci` and is tracked separately.
