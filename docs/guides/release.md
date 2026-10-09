# Cut a release

Status: current
Owner: frob
Decisions: none
Audience: owner

How-to guide (Diataxis: task). Read this if you are the owner cutting a frob
release, here 0.532.0 for the first time. It lists the one-time setup, the
steps for every release, and what to do when a step fails.

Design background is in [releases.md](../design/releases.md). The commands
below were checked against the v2 binary's `--help` and the files named in each
section. Anything that could not be checked is gathered
in the last section, "Not verified".

## What a release does

1. `frob release cut` bumps every crate to one version (the wheels take it from
   Cargo at build time), compiles
   `CHANGELOG.md` from `changelog.d/` fragments, makes one commit on the base
   branch (`experimental` in this repository) and creates one annotated tag per
   product: `frob-v0.532.0` and `grimble-v0.532.0`.
2. Pushing the tags starts `.github/workflows/release.yml`. Only the tag
   `frob-v*` triggers it.
3. The workflow runs these jobs: `plan` (the tag version must equal the
   `frob-cli` crate version), `build` (five archives per product), `wheel` (five wheels per product),
   `smoke` (installs every artifact on a fresh runner), then `release` (GitHub
   release with the archives), `crates` (crates.io) and `pypi` (PyPI).
4. `crates` waits for your approval in the `crates-io` environment and `pypi`
   waits for your approval in the `pypi` environment. Both start after `smoke`
   and are independent: PyPI does not wait for the (possibly hours-long, rate
   limited) crates.io publish. The `release` job needs no approval.

## One-time setup

Do these once, before the first tag is pushed. `frob release status` lists
"registry setup" as an unresolved owner action until this is done.

### 1. GitHub environment `crates-io`

In the repository on GitHub: Settings, Environments, New environment, name
`crates-io`.

- Required reviewers: add yourself.
- Deployment branches and tags: select "Selected branches and tags", add a tag
  rule `frob-v*`.

### 2. GitHub environment `pypi`

Same as above with the name `pypi`: you as required reviewer, and a tag rule
`frob-v*`.

### 3. PyPI trusted publisher

Two PyPI projects are published, `frob` and `grimble` (the `frob` wheel
depends on `grimble` at the same version). `frob` holds v1 up to 0.531.0. Each
project must list this repository's workflow as a trusted publisher. On PyPI: project, Manage, Publishing, add a
GitHub trusted publisher with:

| Field | Value |
|---|---|
| Owner | `lognd` |
| Repository | `frob` |
| Workflow | `release.yml` |
| Environment | `pypi` |

Never add a PyPI token as a repository or environment secret. The workflow
uses trusted publishing, and a test in
`crates/frob-release/tests/release_workflow.rs` fails if the workflow reads a
`secrets.` value other than the crates.io `CARGO_REGISTRY_TOKEN` in the `crates`
job.

### 4. crates.io: the first publish of each crate uses a token

crates.io cannot configure trusted publishing for a crate that does not exist
yet, so the first publish of the 35 shipped crates uses a one-time token. The
`crates` job reads the `crates-io` environment secret `CARGO_REGISTRY_TOKEN` when
one is set (it logs "publishing with the environment's CARGO_REGISTRY_TOKEN") and
otherwise exchanges a trusted-publishing token. A stored token always wins, so it
must be deleted afterwards (section 5).

1. On crates.io create an API token with the `publish-new` and `publish-update`
   scopes (one-time; revoked after the first release). Scope it to the crate
   names if the form allows.
2. In the `crates-io` environment (not the repository, so only the `crates` job
   can read it) add the environment secret `CARGO_REGISTRY_TOKEN` with that
   token.
3. Confirm you own the reserved crate names (the owner action named by
   `frob release status`).
4. Reserve the crate names before the first release (below).
5. Push the tag. A partial publish resumes by re-running; versions already on
   the index are skipped.

#### Reserving names (`cargo dev publish --reserve`)

crates.io limits new crate names far more tightly than new versions: a small
burst, then about one new name per ten minutes, answering 429 with the time to
retry. Publishing 31 new names inside the release job would run for hours, so
reserve the missing names once from your machine with your own token. Each
placeholder is a code-free 0.0.0 crate (name, a description pointing at the
repository, the license), so the release then publishes only new versions.

```sh
cargo dev publish --reserve           # dry run: lists the missing names and the pacing plan
CARGO_REGISTRY_TOKEN=... cargo dev publish --reserve --apply
```

The first five names go out at once, then one every ten minutes; a 429 is waited
out within `--max-wait` (minutes, default 30). When the budget is spent the
command prints the next crate and the earliest retry time and exits 75;
re-run it then. It is resumable: names already on crates.io are skipped.

`cargo dev publish` (the release job) handles 429 the same way: it waits within
`--max-wait` and otherwise stops with exit status 75, naming the next crate and
the retry time, so re-running the job resumes there.

### 5. crates.io trusted publisher, after the first release

Once every crate exists, on crates.io open each crate's settings and add a
trusted publisher with: repository `lognd/frob`, workflow `release.yml`,
environment `crates-io`. Then delete the one-time `CARGO_REGISTRY_TOKEN` secret from the
`crates-io` environment (while it exists the job keeps using it instead of OIDC)
and revoke the token on crates.io. Later releases use the short-lived token the job gets
from `rust-lang/crates-io-auth-action`.

## Every release

Run these in a checkout of the base branch (`experimental`), with a clean tree.
Use the v2 binary; on a machine that still has v1 on `PATH`, call the v2 binary
by its path.

### 1. Check readiness

```sh
frob release status 0.532.0
```

Read the report: exit criteria, open tickets, fragments, CI on the branch tip,
and the unresolved items. The command never fails; it only reports. Add `--text`
for a human view. Fix blockers first. Preview the changelog section without
writing anything:

```sh
frob release changelog --version 0.532.0 --dry-run
```

### 2. Cut the release locally

The milestone `0.532.0` must exist. The cut refuses a dirty tree, a checkout off
the base branch, an existing tag, and a status that is not READY.

```sh
frob release cut 0.532.0
```

This makes the commit `chore(release): cut 0.532.0` and the two tags locally and
records the cut on the milestone. Nothing is pushed yet. Look at it:

```sh
git log -1 --stat
git tag --list '*-v0.532.0'
```

To cut despite a not-ready status, add `--override --reason "text"`; the reason
is recorded on the milestone. Use it rarely.

### 3. Push the commit and the tags

```sh
git push origin experimental
git push origin frob-v0.532.0 grimble-v0.532.0
```

`frob release cut 0.532.0 --push` does both in step 2. The `frob-v0.532.0` tag
starts the release workflow. The `grimble-v` tag starts nothing.

### 4. Approve the environments

Open the run in the repository's Actions tab (workflow `release`).

1. Wait for `plan`, `build`, `wheel` and `smoke` to pass. The `release` job then
   creates the GitHub release with the archives by itself.
2. When `crates` shows "Waiting for review", approve the `crates-io`
   environment. The job prints the publish order in a dry run, then publishes
   the crates in dependency order.
3. `pypi` also shows "Waiting for review" once `smoke` has passed, without
   waiting for `crates`. Approve the `pypi` environment. It uploads the ten smoked wheels (five per product).

Timeouts are in the workflow: `build` and `wheel` 60 minutes, `smoke` 30,
`crates` 120, `pypi` 30. A job whose runner never schedules fails at its timeout
and does not block later releases.

### 5. Verify

```sh
frob release notes --version 0.532.0 --text
gh release view frob-v0.532.0
uv tool install --force frob==0.532.0
frob --version
cargo search frob-cli
```

`frob release notes` prints the CHANGELOG section of that version, which is
what the `release` job uses as the GitHub release body (any lead `notice`
fragment comes first); compare it with what `gh release view` shows. Check also
that PyPI shows 0.532.0 of `frob` and of `grimble`, each with five files, and that crates.io shows the
version for every published crate. (`cargo search frob-cli` is an example name;
use any shipped crate.)

## Dry run (builds and smokes everything, publishes nothing)

Before the first real release, or after changing the build, run the workflow by
hand: `gh workflow run release.yml --ref <branch>` (or Actions, release, Run
workflow). The `workflow_dispatch` trigger builds the five archive sets and the
five wheel sets from that ref and smokes every artifact on fresh runners. No
tag is needed (the tag check is skipped) and the `release`, `crates` and `pypi`
jobs are skipped by `if: github.event_name == 'push'`, so no environment is
requested and nothing is uploaded anywhere. The only exempt target is macOS
x86_64, which is cross-built on an arm64 runner that cannot execute it.

The wheel build and the wheel smoke are the same on every OS: `cargo dev wheel
--out DIR [--target TRIPLE]` and `cargo dev wheel-smoke DIR VERSION` (Rust, in
`crates/gob-dev`; uv builds the maturin environment). Run them locally to
reproduce a wheel failure; there is no shell script to port per platform.

## Resume after a failure

Find the failing point, then use the matching row. Re-running never needs a new
version number.

### The cut failed (steps 2 and 3 above)

Re-run the same command: `frob release cut 0.532.0`. It picks up where it
stopped; the failure matrix is in `crates/frob-release/src/cut.rs`.

| Failure | State left | Re-run |
|---|---|---|
| before the commit (bump, compile, CAS exhausted) | working tree restored | starts fresh |
| after the commit, before any tag | commit on base, no tags | finds the commit by its subject, tags and records |
| between two tags | commit and some tags | creates the missing tags, records |
| after the tags, before the `cut` event | commit and all tags | records only |
| after the `cut` event, before the transition | event written, milestone open | transitions only |
| after the record, the push fails | everything local and recorded | the version counts as cut: run the `git push` commands from step 3 |

A tag of the same name that points at another commit is never moved; the cut
stops with `E-CUT-TAG-EXISTS`. A recorded cut stops with `E-CUT-ALREADY`: cut
the next version instead.

### A tag was made by hand (REL001 fires)

A release tagged with plain `git tag` and already pushed or published is reported by
REL001 as "no recorded release cut". Do not delete a published tag. Record it instead:

```text
frob release adopt 0.1.0 --reason "cut by hand before frob"
```

`adopt` resolves the tags that `[release] tag` and `products` name for the version
(`v{version}` for a one-product repository, so `v0.1.0`), checks that each exists and
points at a commit (annotated or lightweight), and writes the same `cut` event
`release cut` writes, plus an `adopt` event carrying the actor and the reason. The
milestone for the version moves to released; when there is none, one is created already
released to hold the record. Git and the remote are not touched. A repeat returns
`already` and writes nothing. For several versions, run it once per version. REL001 can
still fire afterwards if the workspace version committed at a tag differs from the tag's
version; that is a wrong tag, not a missing record.

### `plan` failed

The tag version differs from the `frob-cli` crate version, or the tag is not
`frob-vMAJOR.MINOR.PATCH`. A tag made by `release cut` agrees by construction.
If you tagged by hand, delete the bad tag locally and on origin, and use
`release cut`; a tag that is already published and correct is recorded with
`frob release adopt VERSION` instead.

### `build`, `wheel` or `smoke` failed

In the Actions run, choose "Re-run failed jobs". The publishing jobs have not
started, because they need `smoke`. If the cause is in the repository (a code or
workflow fix), a re-run uses the workflow file of the tagged commit, so the fix
needs a new patch version (for example 0.532.1) and a new cut.

### `release` (GitHub release) failed

Choose "Re-run failed jobs". If a half-made release exists and the re-run says
the release already exists, delete it with `gh release delete frob-v0.532.0`
(keep the tag) and re-run the job.

### `crates` failed partway

Choose "Re-run failed jobs" and approve `crates-io` again. `cargo dev publish`
skips every crate version already on the index, so the re-run
continues at the first unpublished crate. To see what is published and what is not without
publishing (the dry run prints the publish order; the real run is what skips
versions already on the index):

```sh
cargo dev publish --dry-run
```

You can also run `cargo dev publish` from your machine with
`CARGO_REGISTRY_TOKEN` set; it resumes the same way. The error names the crate:
"re-run to resume here".

A run that stops on the crates.io rate limit prints "stopped (resumable)" with the
next crate and the retry time; re-run the job after that time.

If a crate publishes but the index does not show it in time, the run fails with
a message that the version did not appear on the index; re-run the job.

### `pypi` failed

Choose "Re-run failed jobs" and approve `pypi` again. The upload uses
skip-existing, so files already on PyPI are skipped. The job refuses to run
unless exactly five wheels of each product are present.

### Trusted publishing is rejected

For PyPI or crates.io, compare the publisher entry with the table in the
one-time setup: owner `lognd`, repository `frob`, workflow `release.yml`,
environment `pypi` or `crates-io`. A mismatch in any field is rejected.

## Pin or yank

- To keep users on v1: `uv tool install frob==0.531.0` (see
  [upgrade-from-v1.md](upgrade-from-v1.md)).
- To withdraw a bad release from resolution, yank it. On PyPI use the project's
  release page (Manage, Yank). On crates.io run `cargo yank --version 0.532.0
  <crate>` for each crate. A yank does not delete files and can be undone; fix
  forward with a patch release.

## Lessons from v1 (already in the workflow, do not undo)

- Linux wheels are built in the pinned `manylinux_2_28` image, not `auto`.
  Older images lack a glibc function the vendored tree-sitter sources need.
- The macOS x86_64 archive and wheel are cross-built on the arm64
  `macos-latest` runner. The Intel runner image was retired and a job waiting
  for it blocked every later release.
- Every job has a timeout, so a stuck queue fails the run. The workflow queues
  releases one at a time and never cancels one in progress.
- Every artifact is smoked on a fresh runner before anything is published. The
  cross-built macOS x86_64 artifacts cannot be executed anywhere and are the
  one listed exemption.
- No registry token is stored for PyPI. crates.io uses a one-time token only
  for the first publish of each crate.

## Not verified

- The token fallback was tested as workflow structure only; no real first
  publish has run.
- The GitHub and crates.io and PyPI settings screens (environment tag rules,
  trusted publisher forms, the yank buttons) were written from the owner's
  steps and general knowledge, not exercised here.
- `gh release delete` and `cargo yank` flags were not run.
- `frob release forecast` does not exist yet and is not used.
- That the `release` job body equals the `frob release notes` output was read
  from the workflow, not observed in a real run.
- `frob release status` does not print a link to this guide yet.
- No release has been cut with this workflow; the resume steps for the
  workflow jobs rely on the skip logic in `cargo dev publish` and the
  `skip-existing` setting, which are tested with fakes, not against the real
  registries.
