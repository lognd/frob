# Releases: a scrumban flow wired to milestones, cycles and incremental releases

Status: current
Owner: frob
Decisions: D83
Audience: contributor

Provenance: ACCEPTED (D83, ticket ~5MAFAAY; version scheme decided by the
owner 2026-10-03). Builds on pm-enforcement.md (cycles,
capacity, velocity, forecasts, flow metrics, WIP limits, the PM family),
documentation.md 6 (changelog fragments), monorepo.md 4 (lockstep crate
versions, per-binary tags), build-test-ci.md (the release job), and v1's
release experience (v1 docs/guides/release.md, tickets T-5133, T-5149,
T-5718).

Owner request (2026-10-03): set up milestones for a release track, keep
to scrumban principles, and wire the sprint-planning practices already
designed into an incremental build and release system.

## 1. Vocabulary (one meaning each)

- **Milestone = a version.** A release object (tickets.md 3), never a
  ticket type: a version string, a goal statement, exit criteria
  (acceptance-shaped, each bound to evidence like any ticket), a target
  date or `unscheduled`, and member epics. v1 learned this the hard way:
  sprints were named like versions until T-5133 split them, and its
  1.0.0 milestone ended up as 72 tickets scattered over ten sprints with
  70 leaves outside any epic (T-5149). PM001 and PM002 already require a
  goal and epics; PM034 (below) refuses milestone members outside the
  milestone's epics.
- **Cycle = a time box.** A cadence for review and measurement
  (pm-enforcement.md 4), not a release. Cycles are optional: scrumban
  runs on flow, and cycles give it a heartbeat.
- **Release = cutting a milestone.** It happens when the milestone is
  ready, not when a cycle ends.

## 2. Scrumban policies (explicit, materialized in `[pm]`)

Scrumban takes Kanban's flow (visualize, limit work in progress, pull,
explicit policies, measure) and keeps Scrum's useful cadences. Each
policy below is a materialized knob, so a repository can see and change
its own process.

| Policy | Knob (default) | Enforced by |
|---|---|---|
| **Pull, ranked.** Work is taken from `frob ticket doable`, highest rank first; nobody is assigned work they did not pull. | `[pm] pull = "rank"` | `work` and `start` take the ticket; `doable` orders it |
| **WIP limit per holder.** One ticket in progress per holder (actor plus worktree), so an agent finishes before starting. | `[pm.wip] in_progress_per_identity = 1` | `start` refuses a second (v1 T-5718) |
| **WIP limit for the repository.** The number of in-progress tickets is capped at what the machine can build. In this repository that is two, the disk rule (frob-v2-disk-guard). | `[pm.wip] in_progress = 2` | PM013; `work` refuses past the limit, naming the holders |
| **Replenishment order point.** When ready work falls below a threshold, planning happens then, on demand, not on a calendar. | `[pm] ready_min = 4` (twice the WIP limit) | PM033 replenish (Advisory): "ready queue is 1, below 4: run frob cycle plan or triage" |
| **Classes of service.** `expedite` (a critical bug or security issue: may exceed the repository WIP limit by one, at most one at a time); `fixed-date` (ranked by due date); `standard`; `intangible` (chores and debt, capped as a share of each cycle's points). | `[pm.classes] expedite_max = 1`, `intangible_share = 0.2` | PM013 counts expedite separately; PM035 intangible-share checks the share |
| **Definition of ready.** A ticket enters `ready` only with scope, acceptance and points. | `[pm] ready_requires` | PM012, PM005 |
| **Definition of done.** Close guards: criteria evidenced, docs touched or excepted, no open children, changelog fragment. | `[pm] done_requires` (pm-enforcement.md 3) | the close guard, REL003 |
| **Cadences.** Replenishment on demand (order point); cycle review at each cycle close (commitment ratio, flow metrics, one retro note event); release on demand when a milestone is ready; a dev build on every green land. | `[pm] cycle_days = 7` | `frob cycle close`, `frob release status` |
| **Bucket planning.** Only the next milestone is planned in detail; later ones keep a goal and epics and stay `unscheduled` until `frob forecast` has the history to date them. | none | PM001 allows `unscheduled` |

## 3. Every land keeps main releasable

Incremental releases depend on main always being shippable:

- The land gate (`frob check`) and whole-workspace evidence already hold
  for every land.
- Every user-visible change carries a changelog fragment
  (`changelog.d/<ulid>.<type>.md`, REL003 at close), so release notes
  are ready at all times and no one writes them at release time.
- A ticket's milestone is set when it is planned. `frob release status`
  shows what a cut would contain at any moment.

## 4. Verbs

| Verb | What it does |
|---|---|
| `frob milestone new VERSION --goal "..." [--target DATE]` | creates the release object; exit criteria are added as `--criterion` and bound to evidence like acceptance |
| `frob milestone add EPIC VERSION` | adds an epic; tickets join through their epic (PM034 keeps it that way) |
| `frob milestone criterion add VERSION TEXT` / `remove VERSION N` | edits the exit criteria; a removal records the `moved` map (old position to new, 0 when removed) so evidence follows its criterion |
| `frob milestone evidence add VERSION --provider P --ref R [--accepts N]...` / `list VERSION` | captures a record with the same providers, allowlist and format as `ticket evidence add` and offers it for exit criteria; `milestone show` prints each criterion as `bound` or `unbound` with the binding evidence (latest record per provider, ref and criterion decides; only measured, passing records bind; `--provider attestation --statement T [--fact F]...` is a listed attester's statement for criteria no tool measures, shown as `attested`, security.md 2.3). `milestone criterion remove` reports the evidence that loses its criterion (`lost_evidence`, as `ticket update` does) |
| `frob release status [VERSION]` | readiness: every exit criterion evidenced; no open ticket in the milestone's epics; CI green on the tip; fragments compile; GEN001 and the pack lock clean. It also prints what is left, the forecast for it (pm-enforcement.md 5) and the changelog preview. It never fails a check; it reports. |
| `frob release cut VERSION` | requires status ready (or `--override --reason`, recorded as an event). Bumps the lockstep version of every crate (monorepo.md 4); compiles CHANGELOG.md from the fragments and removes them; commits on main through the land machinery (CAS, one commit); tags one tag per configured product (section 4a). Pushing the tag starts the release job. As built: `frob release cut VERSION [--override --reason TEXT] [--push]` refuses a dirty tree, a checkout off the base branch, an existing tag and a not-ready status (exit 3 with the remedy); the override reason is a `override` event on the milestone; the commit is `chore(release): cut VERSION`; tags are annotated, local unless `--push`, one per `[release] products` entry named by `[release] tag` (this repository: `frob-v` and `grimble-v` tags); the milestone gets a `cut` event (version, commit, tag names and oids; REL001 reads it) and moves to `released`. A failure after the commit resumes by re-running the same command (failure matrix in `crates/frob-release/src/cut.rs`). |
| `frob release adopt VERSION [--reason TEXT]` | records tags made by hand as the version's cut, so a published tag is never deleted to satisfy REL001. It resolves the tags the configured `[release] tag` pattern and `products` name for VERSION, checks each exists and peels to a commit (annotated or lightweight), and appends the `cut` event `release cut` writes (version, commit, tag names and oids) followed by an `adopt` event (version, optional reason; the actor is the event envelope's), then moves the version's milestone to `released`; with no milestone it creates one, already released, because cut events live in a milestone's log. The marker is a separate event kind rather than a field of `cut` because `CutData` denies unknown fields: an older binary reads the unknown kind as `other` and the `cut` event unchanged, so it keeps working on the ledger (and still treats the tag as cut). Never writes a ref or touches the remote; idempotent (a repeat returns `already`); a missing tag is `E-ADOPT-NO-TAG`, one that is not a commit `E-ADOPT-NOT-COMMIT`. REL001's remedy names it first |
| `frob release notes --version X` | prints the body of that version's CHANGELOG.md section (heading and integrity marker removed) as `data.notes`, and with `--text` the section alone, raw, with no envelope; the release job feeds it to `gh release create --notes-file` via `--text > notes.md` (the linux archive's own binary, no markdown parsed and no jq in shell) and does not use `--generate-notes`, so the compiled section is the whole release body. It reuses `changelog::split` and `heading_version`; a missing section is `E-CHANGELOG-NO-SECTION` |
| `frob release bump VERSION [--dry-run] [--allow-downgrade]` | sets the one lockstep version: `[workspace.package] version` (added when absent), every member made to inherit it with `version.workspace = true` (one line to edit per release, no member can drift), the `version` of intra-workspace path dependencies, a static wheel `pyproject.toml` version, then `Cargo.lock` through an offline `cargo update --workspace`; format-preserving, idempotent (a repeat reports `already`), refuses a version below the current one without `--allow-downgrade`, and re-runs REL002 afterwards. `release cut` calls it |
| `frob release forecast VERSION` | time to release: the forecast of the last blocking ticket plus the measured land-to-release lag |
| `frob cycle new/plan/assign/close/velocity` | as pm-enforcement.md 4; `plan` fills to capacity from ready work in rank order, preferring the next milestone |
| `frob board` | the scrumban board: columns by category, WIP limits shown, expedite lane, aging per card. As built: `frob board [--width N] [--cards N]`; columns triage, todo (`doable` order first), in-progress, blocked (a todo ticket with an open blocker; in-progress tickets stay in their column so the count matches PM013) and done (last 7 days); epics are left off. The in-progress header is `count/limit` from the one WIP count (`frob_pm::rules::wip::read`, shared with PM013 and `work`), so stale holders are marked `STALE` and not counted, and an exceeded limit shows `!` (red with color). The expedite lane, when `[pm.classes] expedite_max` is above 0, lists every live expedite ticket on top. Each card shows handle, points, age (since the ticket entered its current category, from `transition` events: `<1m`, `5m`, `7h`, `3d`), title, lease holder and due date. Text is ASCII, sized to `--width`, else `COLUMNS` on a terminal, else 100 (stacked below 16 characters per column); `--json` carries the same typed board in `data.board`; `--brief` (D104/D105) is the compact view of the same board: NOW (in-progress with holder, worktree, age and last observed signal and its time since, inferred from the lease heartbeat, commits on the ticket branch, and evidence, land and move events, never declared), NEXT (doable order) and BLOCKED (with open blockers), in `data.brief` under `--json`; other columns list at most `--cards` (default 8) cards and count the rest. |

New rules: **PM033 replenish** (Advisory, the order point), **PM034
milestone-member-outside-epics** (Warning, the v1 T-5149 failure),
**REL001 release-without-cut** (Error: a product tag, per the configured tag pattern, not made by
`release cut`, so versions, changelog and tags never disagree), and
**REL002 lockstep-version-mismatch** (Error: workspace crates whose
versions differ). REL001 was v1's debt rule; its id is reused only
because exceptions.md 6 retired the v1 meaning, and the rule page says
so.

## 4a. Products, tag pattern and the changelog in any repository

`release cut`, `release changelog` and REL001 know no product names of
their own; they read `[release]` in `frob.toml` (reported by cloc, the first
consumer repository):

| Key | Default | Meaning |
|---|---|---|
| `tag` | `"v{version}"` | tag name pattern; `{version}` is required, `{product}` expands to each product name |
| `products` | `[]` | the products a release ships, one tag each; empty means one product named after the repository (the `origin` URL's last segment, else the main checkout's directory name) |

A repository that sets neither gets one tag, `vVERSION`. With several
products the pattern must contain `{product}` (otherwise the tags would
collide, and the cut refuses). This repository sets `products = ["frob",
"grimble"]` and `tag = "{product}-v{version}"`, so its tags are unchanged.
REL001 treats a tag as a product tag when it matches the pattern for a
configured product and the rest parses as a version; all other tags (for
example v1's `v0.531.0` here) are ignored.

The date of a compiled changelog section is the UTC calendar day of the command's clock (`--date` overrides it), never the machine's local zone, so a cut at 00:06 UTC is dated the same everywhere (time.md, D93).

The compiled changelog section has product headings (`### frob`) only when
several products are configured; with one product the entries are listed
under their type headings, whatever product prefix a fragment names. A `notice`
fragment (`changelog.d/<ulid>.notice.md`, at most one per section) is rendered
first, as a paragraph above the product and type headings, and is covered by the
section hash like everything else. A fresh
CHANGELOG.md links `CHANGELOG-v1.md` only when that file exists.

**Adopting a hand-written CHANGELOG.md.** A file that does not start with
the generated-file marker is the author's. `release changelog` inserts the
generated section directly above the first version heading (`## 1.2.0`,
`## [1.2.0] - date`, `## v1.2.0`; `## Unreleased` is not one), keeps
everything above it as it was, and puts the integrity marker on the generated
section only. Unmarked sections of such a file are never verified; marked
ones are, so a hand edit of a generated section is still detected. A file
with no version heading gets the section appended. A file that starts with
the marker keeps the strict rule: every section must carry its marker.

## 5. Channels and version scheme

| Channel | When | Where | Who installs it |
|---|---|---|---|
| dev | every green land on main | GitHub prerelease `dev` (artifacts replaced each time); nothing published to registries | people testing the tip |
| preview (0.53X) | `release cut` of a 0.53X milestone | crates.io, PyPI and a GitHub release | everyone who installs frob; no stability promised (0.x) |
| stable | `release cut` of 1.0.0 and later | crates.io, PyPI, GitHub release | everyone, with compatibility guarantees |

**Version scheme (owner decision 2026-10-03).** v2 continues the
existing line: PyPI's `frob` ships v1 as 0.531.0 (alpha, no guarantees),
and v2's releases are 0.532.0, 0.533.0 and so on, one minor number per
milestone, with patch releases (0.532.1) for fixes between milestones.
1.0.0 is the first stable version, the first with compatibility
guarantees. Every crate of the workspace and the wheel carry the same
number (monorepo.md 4). Under 0.x semver no stability is promised, and
installing or upgrading `frob` after 0.532.0 gives the rewrite: the
0.532.0 release notes say so plainly, with the v1-to-v2 differences and
how to pin 0.531.0.

## 6. The release job (lessons carried from v1)

v1 docs/guides/release.md records what went wrong; each lesson becomes
part of the job's design:

- **Wheels:** manylinux `2_28`, not `auto`. Vendored tree-sitter C
  sources need glibc 2.19 or later (v1 T-4464: `le16toh` undefined on
  manylinux2014).
- **macOS:** x86_64 is cross-built on `macos-latest` (arm64), never on a
  retired Intel image. A retired label queued a job for four hours and
  blocked every later release behind the release concurrency group
  (T-4470). Every job has a timeout, so a stuck queue fails instead of
  waiting.
- **Artifact smoke:** each built artifact is installed into a clean
  environment and runs real commands (`frob doctor`, `frob check` on a
  fixture repository). As built, wheels (`cargo dev wheel-smoke`) and
  standalone archives (`packaging/smoke/archive-smoke.sh`) share
  `packaging/smoke/fixture-loop.sh`: init, doctor, check, a ticket with
  one criterion, work, edit, check, command-provider evidence, a changelog
  fragment, land, then the ticket is closed done and `ticket doctor` is
  clean. The wheel smoke takes the whole wheel directory and installs from
  it only (`--no-index --find-links`, never the index): grimble alone, frob
  alone (which must pull grimble at the same version, then the loop), and
  `uv tool install frob` (grimble not on `PATH`, yet `frob doctor` finds it
  beside frob). The loop runs twice: on the build runner right after the build,
  and again in the `smoke` job, a separate matrix job that downloads the
  uploaded wheel and archive onto a fresh runner (so a runtime dependency
  only the build machine has is caught); every publishing job needs
  `smoke`. A target that cannot be executed on its runner
  is listed as an explicit, tested exemption, never faked (v1's
  `_SMOKE_EXEMPT_TARGETS`). `archive-smoke.sh PRODUCT ARCHIVE` smokes one
  product archive (frob runs the fixture loop, grimble runs
  `grimble --version`); the workflow names each archive explicitly and a
  step fails if `target/distrib` holds anything but the product archives.
- **Dry run:** `release.yml` also has a `workflow_dispatch` trigger that runs the
  shared plan, build, wheel and smoke from the dispatched ref with no tag
  check; every publishing job (`release`, `crates`, `pypi`) is guarded by
  `github.event_name == 'push'`, so a dispatch publishes nowhere and never
  requests an environment (pinned by `release_workflow.rs`).
- **Archives:** exactly one per product binary per target (D87,
  products.md 6), named after the dist package: `frob-cli-<target>.tar.xz`
  (`.zip` on windows) holding `frob`, and `grimble-<target>` holding
  `grimble`, each with a `.sha256`; crunk joins as one more entry,
  `crunk-<target>`. cargo-dist 0.32 names an archive after its package
  and has no rename option, so the frob archive keeps the `frob-cli`
  package name (the crates.io name, products.md 6). `dist-workspace.toml`
  sets `dist = false` as the workspace default and each product package
  opts in with `[package.metadata.dist] dist = true`; no published crate
  declares a binary that is not a product (test helpers such as
  `fake-sibling` live in the `publish = false` crate `gob-testsupport`).
  `crates/frob-release/tests/products.rs` pins the binary set, the dist
  set and the archive names the smoke and upload steps use.
- **Build matrix:** cargo-dist per binary (monorepo.md 4): linux
  x86_64 and aarch64, macOS arm64 and x86_64 (cross), windows x86_64.
  PyPI gets one wheel set per product, each carrying only its own
  binary; `frob` depends on `grimble` and `crunk` at the same version
  (products.md 6, D87). As built, `packaging/pypi/products.toml` is the
  one product list (frob, grimble; crunk is one more entry): `render.py`
  renders each product's maturin project from one template, and the
  version is the Cargo lockstep version read at build time, so the
  `grimble==VERSION` pin of the frob wheel and every wheel version are
  equal by construction (no checked-in version to bump or drift, REL002
  has nothing to compare). `wheel` builds both products per target into
  one `wheel-<target>` artifact; the `pypi` job checks five wheels per
  product before uploading.
- **Pinned installers:** inside the manylinux containers rustup-init is
  downloaded from its versioned static URL
  (`static.rust-lang.org/rustup/archive/<version>/<triple>/rustup-init`)
  and checked against a per-architecture sha256 before it runs, never
  piped from `sh.rustup.rs`; maturin is installed with `uv pip install
  --require-hashes` from `packaging/pypi/maturin-requirements.txt`
  (exact version, wheel hashes from PyPI). A test fails if either loses
  its hash check.
- **No sdist:** the release ships no PyPI source distribution. The wheel
  bundles prebuilt binaries and an sdist would need the whole workspace
  (maturin builds `frob-cli` from the repository, not from
  `packaging/pypi` alone); source ships through crates.io and git, and a
  source install of the wheel would be an unsmoked, unhashed build path.
- **Publishing:** crates.io in dependency order and in lockstep. A
  partial publish resumes from the first unpublished crate, never
  re-bumps. Registry tokens live only in the release environment, and
  security.md's CI rules apply. Every crate publishes (`publish` is set
  per crate, never workspace-wide) except the dev-only crates, which
  carry `publish = false` and are exactly `gob-dev` (the `cargo dev`
  runner) and `gob-mdtest` (the corpus test harness); `grimble` ships
  as a preview in 0.532.0 with the `grimble-*` crates. The root `Cargo.toml` comment repeats this list. Every
  path dependency on a shipped crate carries a `version`, which `frob
  release bump` keeps in lockstep. The `crates` job publishes with the
  `crates-io` environment's `CARGO_REGISTRY_TOKEN` secret when one is
  set and through the OIDC action otherwise (crates.io cannot configure
  trusted publishing for a crate that does not exist yet, so the first
  publish needs the token; the owner then configures trusted publishing
  per crate and deletes the secret). crates.io rate-limits new crate
  names (a small burst, then about one per ten minutes, answered with
  429 and a retry time), so `cargo dev publish` waits out a 429 within
  `--max-wait` and otherwise exits 75 naming the next crate and the retry
  time, and `cargo dev publish --reserve [--apply]` pre-publishes 0.0.0
  placeholders for missing names (paced, resumable, dry run by default).
  The `pypi` job needs only `artifacts` (smoke), not `crates`: the two
  registries publish independently.

## 6a. Details (closing the 0.532.0 planner's gaps)

- **Storage of milestones and cycles.** They are ledger objects with the
  same event-sourced storage as tickets: an object directory holding a
  frontmatter file folded from its own events, identified by a ULID,
  with the version (milestones) or the dates (cycles) as aliases. Kinds
  `milestone` and `cycle` join tickets.md 2a (`create`, `field`,
  `member` for epic and ticket membership, `criterion`, `transition`).
  In the milestone-1 layout they live at `tickets/_milestones/<ULID>/`
  and `tickets/_cycles/<ULID>/`; on the ticket branch at `_milestones/`
  and `_cycles/` (navigation.md 3.1). Membership is an event on the
  object, never a field on the ticket, so moving a ticket between
  cycles is one append.
- **One version, per-product tags.** Every crate and the wheel carry one
  lockstep version (section 5); `release cut` tags each configured product
  at the same commit (section 4a; monorepo.md 4, updated). Here that is
  `frob-vVERSION` and `grimble-vVERSION`, plus `crunk-v` once it exists.
- **Forecast in `release status`.** Printed only when `[pm] min_history`
  cycles exist; before that the line is Unresolved with the sample
  count. `frob release forecast` ships with 0.536.0.
- **What the wheels carry (D87).** One binary per package: the
  `frob` wheels carry `frob` and depend on `grimble` (and `crunk` once it
  ships from this repository) pinned to the same version; the `grimble`
  wheels carry `grimble`, a preview from 0.532.0 (its `--version` says
  preview until 0.533.0).
- **Trigger and gates.** Pushing a `frob-v*` tag starts the build and
  smoke jobs; the crates.io and PyPI publish jobs run in a protected
  environment that needs the owner's approval (v1's reviewer gate,
  kept).
- **CHANGELOG.** The v1 history moves to `CHANGELOG-v1.md`, linked from
  the top of a new `CHANGELOG.md` that `release changelog` compiles from
  fragments; the first section is 0.532.0.
- **Dev channel branch.** "main" in section 5 means the repository's
  default branch; in this repository that is `experimental` until main
  is cut over.
- **Dev channel workflow.** The dev channel is the last two jobs of
  `.github/workflows/ci.yml`, not a separate workflow: `workflow_run`
  fires only from the default branch's copy of a workflow file (here
  `main` still holds v1's), so a `workflow_run` dev workflow never ran,
  and it is the trigger zizmor flags (CI006). `dev-artifacts` and
  `dev-publish` need every test job and run only when the event is a
  push, the repository is this one and `github.ref` is a dev branch
  (`refs/heads/experimental`, listed in both `if` lines); pull requests
  and pushes to other branches skip them. `dev-artifacts` rebuilds the
  cargo-dist archives of the tested sha by calling the reusable
  `.github/workflows/build-smoke.yml`, the one source of the matrix, the pinned
  dist and the build and smoke steps that `release.yml` calls too (dev
  passes `wheels: false` and no secrets). `dev-publish` is the only
  `contents: write` job in the workflow: it replaces
  the `dev` prerelease assets add-then-prune: new assets carry the sha in
  their names, the tag and notes move, and the previous assets are
  deleted last, so a failed run leaves the previous ones. It publishes
  nothing to PyPI or crates.io. `crates/frob-release/tests/dev_workflow.rs`
  pins these invariants and that both workflows call the shared one;
  publishing is not a `cargo dev ci` step, so the parity test ignores it.
- **CI status in `release status`.** Read through the hosting API (`gh`
  for GitHub) for the tip commit; without network or a token the line is
  Unresolved, never assumed green. The commit is the base-branch tip a
  cut would release (the report names its sha); owner and repository come
  from the `origin` remote, and `gh api` reads its check runs and combined
  status. All completed and succeeded or skipped (at least one) is green and
  adds nothing; any failure, cancellation or timeout is a blocker naming the
  checks and links; unfinished checks are a blocker ("CI still running");
  no checks, `gh` missing or unauthenticated, no network or a non-GitHub
  origin is an Unresolved line with the exact reason and remedy and, because
  `[release] require_ci` defaults to true, also a blocker (false reports it
  as Unresolved only). `release cut` runs the same gate, so a red tip cannot
  be cut without `--override`.
- **Owner actions before the first publish.** Configure trusted
  publishing on PyPI (`frob`) and, once the first publish has created the
  crates, on crates.io (the first publish uses a token in the release
  environment); confirm ownership of the reserved
  crate names (products.md 5). These are human steps, listed by
  `frob release status` as Unresolved items until done.
- **Rule numbers.** PM035 intangible-share (Warning) is new; PM014 keeps
  its pm-enforcement.md meaning (milestone without forecast). PM010 to
  PM012 and PM035 are not in 0.532.0 (cycles ship at minimum scope).

## 7. The v2 milestone list

Each milestone is a usable increment. Epics are the existing ones
(planner tree of 2026-10-04 plus the milestone-2 work).

| Milestone | Goal | Contents (epics and areas) | Exit criteria (abridged) |
|---|---|---|---|
| **0.532.0 "frob in your repository"** | someone outside this repository can install frob and run its whole loop | frob core verbs (done); this release track (milestones, `release status/cut`, REL001-002, PM033-034, WIP limits, board); the release job; `frob init` on a fresh repository | binaries and wheel install on the five targets with artifact smoke; two outside repositories (the owner's cloc-style tool and the mdcat fork) managed by frob for two cycles with no ledger data loss; CHANGELOG compiled from fragments |
| **0.533.0 "rules you can write"** | rules are written in GRL and taught by the tool | area:grl (front end, executor, std pack, rule verbs); area:diagnostics (teaching, explain, fixes); grimble preview binary | the ten GRL acceptance rules pass; the second newcomer test; B1 within target |
| **0.534.0 "tickets anyone can read"** | the ledger lives on its branch, with navigation and a GitHub mirror | area:navigation; area:mirror (reconcile, proposals); migration of this repository's ledger | TICK004-007 green; mirror model-checked properties hold in the implementation's property tests; reindex replay check green |
| **0.535.0 "plugins you can trust"** | repository and external packs run safely | area:packs; area:security; G10, G14, G17, NEAT families | security audit findings closed or recorded; trust review usability test; B2-B3 within target |
| **0.536.0 "plans you can trust"** | forecasting and flow metrics from real history | PM family, cycles, forecasts, `frob stats`; docs site | forecasts validated against two months of history |
| **0.537.0 "design tokens, one binary"** | crunk ships from the monorepo | epic ~X0SN72M: crunk binary and registration, crunk.toml, TS/TSX and CSS ingest, token model and export, the core token rule families (Rust first), fix, query, parity with the Python crunk, preview release | parity harness green against the Python crunk corpus; crunk preview installs from PyPI and archives; the Python crunk retired (owner steps) |
| **0.538.0 "web and system-design packs"** | the D89 packs | crunk-web (A11Y, SEO, LAUNCH, WEBPERF markup), crunk gallery (opt-in), epic ~5NR79CM grimble-websec and grimble-sysdesign | each pack loads through the pack loader with its families tested; packs off by default |
| **1.0.0** | stable | everything above | 30 days managing three or more repositories with no data loss; no open critical or high security finding; upgrade path from v1 documented |

Milestones beyond 0.532.0 stay `unscheduled` until there is history
(bucket planning, section 2).
