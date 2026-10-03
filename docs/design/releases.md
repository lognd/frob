# Releases: a scrumban flow wired to milestones, cycles and incremental releases

Status: ACCEPTED (D83, ticket ~5MAFAAY; version scheme decided by the
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
| `frob milestone evidence add VERSION --provider P --ref R [--accepts N]...` / `list VERSION` | captures a record with the same providers, allowlist and format as `ticket evidence add` and offers it for exit criteria; `milestone show` prints each criterion as `bound` or `unbound` with the binding evidence (latest record per provider, ref and criterion decides; only measured, passing records bind) |
| `frob release status [VERSION]` | readiness: every exit criterion evidenced; no open ticket in the milestone's epics; CI green on the tip; fragments compile; GEN001 and the pack lock clean. It also prints what is left, the forecast for it (pm-enforcement.md 5) and the changelog preview. It never fails a check; it reports. |
| `frob release cut VERSION` | requires status ready (or `--override --reason`, recorded as an event). Bumps the lockstep version of every crate (monorepo.md 4); compiles CHANGELOG.md from the fragments and removes them; commits on main through the land machinery (CAS, one commit); tags `frob-vVERSION` (plus `grimble-v` and `crunk-v` when those binaries are in the milestone). Pushing the tag starts the release job. |
| `frob release bump VERSION [--dry-run] [--allow-downgrade]` | sets the one lockstep version: `[workspace.package] version` (added when absent), every member made to inherit it with `version.workspace = true` (one line to edit per release, no member can drift), the `version` of intra-workspace path dependencies, a static wheel `pyproject.toml` version, then `Cargo.lock` through an offline `cargo update --workspace`; format-preserving, idempotent (a repeat reports `already`), refuses a version below the current one without `--allow-downgrade`, and re-runs REL002 afterwards. `release cut` calls it |
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
- **One version, per-binary tags.** Every crate and the wheel carry one
  lockstep version (section 5); `release cut` tags `frob-vVERSION` and,
  for each other binary that ships in the release, `grimble-vVERSION`
  and `crunk-vVERSION` at the same commit (monorepo.md 4, updated).
- **Forecast in `release status`.** Printed only when `[pm] min_history`
  cycles exist; before that the line is Unresolved with the sample
  count. `frob release forecast` ships with 0.536.0.
- **What the wheel bundles.** The binaries built in that release: `frob`
  always, `grimble` from 0.532.0 as a preview (its `--version` says
  preview until 0.533.0), `crunk` once it exists.
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
- **CI status in `release status`.** Read through the hosting API (`gh`
  for GitHub) for the tip commit; without network or a token the line is
  Unresolved, never assumed green.
- **Owner actions before the first publish.** Configure trusted
  publishing on PyPI (`frob`) and crates.io where available (otherwise a
  token in the release environment); confirm ownership of the reserved
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
| **1.0.0** | stable | everything above | 30 days managing three or more repositories with no data loss; no open critical or high security finding; upgrade path from v1 documented |

Milestones beyond 0.532.0 stay `unscheduled` until there is history
(bucket planning, section 2).
