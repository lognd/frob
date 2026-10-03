# Releases: a scrumban flow wired to milestones, cycles and incremental releases

Status: ACCEPTED as the design (D83, ticket ~5MAFAAY); the version scheme
in section 5 awaits the owner. Builds on pm-enforcement.md (cycles,
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
| **Classes of service.** `expedite` (a critical bug or security issue: may exceed the repository WIP limit by one, at most one at a time); `fixed-date` (ranked by due date); `standard`; `intangible` (chores and debt, capped as a share of each cycle's points). | `[pm.classes] expedite_max = 1`, `intangible_share = 0.2` | PM013 counts expedite separately; PM014 checks the share |
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
| `frob release status [VERSION]` | readiness: every exit criterion evidenced; no open ticket in the milestone's epics; CI green on the tip; fragments compile; GEN001 and the pack lock clean. It also prints what is left, the forecast for it (pm-enforcement.md 5) and the changelog preview. It never fails a check; it reports. |
| `frob release cut VERSION` | requires status ready (or `--override --reason`, recorded as an event). Bumps the lockstep version of every crate (monorepo.md 4); compiles CHANGELOG.md from the fragments and removes them; commits on main through the land machinery (CAS, one commit); tags `frob-vVERSION` (plus `grimble-v` and `crunk-v` when those binaries are in the milestone). Pushing the tag starts the release job. |
| `frob release forecast VERSION` | time to release: the forecast of the last blocking ticket plus the measured land-to-release lag |
| `frob cycle new/plan/assign/close/velocity` | as pm-enforcement.md 4; `plan` fills to capacity from ready work in rank order, preferring the next milestone |
| `frob board` | the scrumban board: columns by category, WIP limits shown, expedite lane, aging per card |

New rules: **PM033 replenish** (Advisory, the order point), **PM034
milestone-member-outside-epics** (Warning, the v1 T-5149 failure),
**REL001 release-without-cut** (Error: a `frob-v*` tag not made by
`release cut`, so versions, changelog and tags never disagree), and
**REL002 lockstep-version-mismatch** (Error: workspace crates whose
versions differ). REL001 was v1's debt rule; its id is reused only
because exceptions.md 6 retired the v1 meaning, and the rule page says
so.

## 5. Channels and version scheme

| Channel | When | Where | Who installs it |
|---|---|---|---|
| dev | every green land on main | GitHub prerelease `dev` (artifacts replaced each time); nothing published to registries | people testing the tip |
| alpha | `release cut` of an alpha milestone | crates.io and PyPI as prereleases, plus GitHub release | `uv tool install --prerelease allow frob` or `cargo install frob-cli --version 2.0.0-alpha.N` |
| stable | `release cut` of 2.0.0 and later | crates.io, PyPI, GitHub release | everyone |

**Version scheme (OWNER).** PyPI's `frob` already ships v1 as 0.531.0
(alpha, no guarantees). Proposed: v2 is the 2.0.0 line. Prereleases are
`2.0.0a1` on PyPI and `2.0.0-alpha.1` on crates.io and in git tags (the
same version in each registry's syntax). Consequences:

- `pip install frob` and `uv tool install frob` keep installing v1
  until 2.0.0 stable, because installers skip prereleases unless asked.
  Nobody is upgraded by surprise.
- v2's crates start at 2.0.0-alpha.1 in lockstep with the wheel, so one
  number means one release everywhere.

The alternative, continuing 0.6xx on PyPI, is monotonic but would
publish the rewrite to everyone who runs v1 at the next install.

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
  fixture repository). A target that cannot be executed on its runner
  is listed as an explicit, tested exemption, never faked (v1's
  `_SMOKE_EXEMPT_TARGETS`).
- **Build matrix:** cargo-dist per binary (monorepo.md 4): linux
  x86_64 and aarch64, macOS arm64 and x86_64 (cross), windows x86_64.
  The PyPI wheel bundles the binaries (`frob` bundles all three,
  products.md).
- **Publishing:** crates.io in dependency order and in lockstep. A
  partial publish resumes from the first unpublished crate, never
  re-bumps. Registry tokens live only in the release environment, and
  security.md's CI rules apply.

## 7. The v2 milestone list

Each milestone is a usable increment. Epics are the existing ones
(planner tree of 2026-10-04 plus the milestone-2 work).

| Milestone | Goal | Contents (epics and areas) | Exit criteria (abridged) |
|---|---|---|---|
| **2.0.0-alpha.1 "frob in your repository"** | someone outside this repository can install frob and run its whole loop | frob core verbs (done); this release track (milestones, `release status/cut`, REL001-002, PM033-034, WIP limits, board); the release job; `frob init` on a fresh repository | binaries and wheel install on the five targets with artifact smoke; two outside repositories (the owner's cloc-style tool and the mdcat fork) managed by frob for two cycles with no ledger data loss; CHANGELOG compiled from fragments |
| **2.0.0-alpha.2 "rules you can write"** | rules are written in GRL and taught by the tool | area:grl (front end, executor, std pack, rule verbs); area:diagnostics (teaching, explain, fixes); grimble preview binary | the ten GRL acceptance rules pass; the second newcomer test; B1 within target |
| **2.0.0-alpha.3 "tickets anyone can read"** | the ledger lives on its branch, with navigation and a GitHub mirror | area:navigation; area:mirror (reconcile, proposals); migration of this repository's ledger | TICK004-007 green; mirror model-checked properties hold in the implementation's property tests; reindex replay check green |
| **2.0.0-alpha.4 "plugins you can trust"** | repository and external packs run safely | area:packs; area:security; G10, G14, G17, NEAT families | security audit findings closed or recorded; trust review usability test; B2-B3 within target |
| **2.0.0-beta.1 "plans you can trust"** | forecasting and flow metrics from real history | PM family, cycles, forecasts, `frob stats`; docs site | forecasts validated against two months of history |
| **2.0.0** | stable | everything above | 30 days managing three or more repositories with no data loss; no open critical or high security finding; upgrade path from v1 documented |

Milestones beyond alpha.1 stay `unscheduled` until there is history
(bucket planning, section 2).
