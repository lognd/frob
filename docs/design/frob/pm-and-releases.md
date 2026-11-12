# Project management and releases: enforcement, cycles, flow and scrumban releases

Status: current
Owner: frob
Decisions: D17, D19, D36, D83, D90, D105, D135
Audience: contributor

How frob enforces project management (part 1 to 10: hierarchy, stories, quality goals, ready and done, cycles
and capacity, estimates, flow and WIP, the PM rule family, agents and the design join) and how a scrumban flow
is wired to milestones, cycles and incremental releases (part 11 to 19). Merged from the former
pm-and-releases.md and pm-and-releases.md. Cycles, capacity and WIP are stated once: the mechanics in sections 5 and 7,
the policy knobs and their defaults in the policy table of section 12.

Provenance: pm-enforcement: written under T-0001 (a v1-format id that migrates with an alias). Owner direction
2026-10-01: enforce good project-management practice, not just record it: structured user stories for
functional goals, velocity-aware cycle commitments, and real estimates of time to deploy. Milestone 2 or later
(D36): cycles, capacity, forecasts, flow metrics and the PM rule family; milestone 1 keeps only the optional
story fields of section 2. Releases: ACCEPTED (D83, ticket ~5MAFAAY; version scheme decided by the owner
2026-10-03). Builds on shared/documentation.md 6 (changelog fragments), shared/charter.md 4 (lockstep crate versions,
per-binary tags), shared/build-test-ci.md (the release job), and v1's release experience (v1
docs/guides/release.md, tickets T-5133, T-5149, T-5718). Owner request (2026-10-03): set up milestones for a
release track, keep to scrumban principles, and wire the sprint-planning practices already designed into an
incremental build and release system.

## 1. The hierarchy and what each level must carry

| Level | Required before it can leave `triage` | Enforced by |
|---|---|---|
| milestone (a release object, not a ticket type) | goal statement, target date or `unscheduled`, at least one epic | PM001 |
| epic | outcome statement, success metric, milestone | PM002 |
| story (functional goal) | a structured user story (section 2), acceptance criteria in Given/When/Then, size, parent epic | PM003-PM006 |
| story (quality objective) | attribute, resolvable driver, registered metric, baseline, target, runnable proof (section 3) | PM020-PM029 |
| chore | small, no public-surface change, an `enabler-for` link or a parent epic | PM026, PM030 |
| task, bug, chore | parent story or an explicit `no-story reason` (bugs and chores may stand alone; a task with user-visible behavior may not) | PM007 |

Every field is checked at write time by the verb and again by the PM
rule family (crate `frob-pm`) in `frob check`, so a hand-edited or
migrated ticket is caught too. A write-time refusal follows the severity
of the rule: the verb refuses (with the exact remedy) only when the
rule's effective severity is Error, and otherwise succeeds with the
finding as a warning in the envelope (docs/design/shared/rules.md section 7 composes the
strictness knobs). Rules are declared with
the same derive as everything else and are configurable per repo
(`[pm] stories_required = true`).

## 2. User stories are structured, not prose

```toml
[story]
as_a = "release engineer"
i_want = "frob land to refuse a squash from a stale base"
so_that = "a landed feature cannot be silently reverted"
```

`frob ticket new --type story --as-a ... --i-want ... --so-that ...`
writes the three fields; the title is generated ("As a release
engineer, I want ...") unless overridden. The body renders them. Checks:

- PM003: all three parts present, each at least three words, `as_a`
  names a persona from `[pm.personas]` (declared list, like labels) or
  is explicitly `--persona-new NAME` which adds it.
- PM004: `so_that` is not a restatement of `i_want` (token overlap
  threshold) and does not contain implementation nouns from a
  configurable deny list ("database", "refactor") so the story states
  value, not mechanism.
- PM005: acceptance criteria exist and each is Given/When/Then or an
  explicit `--criterion-free-form reason`.
- PM006: INVEST checks: size at or under `[pm] max_story_points`;
  no `blocks` edge to another story in the same cycle (independent);
  points set before `ready` (estimable); at least one criterion bound
  to evidence before `done` (testable, already in tickets.md).

Implemented (PM003-PM007, warn by default, error under `[pm] strict`):
each rule examines live stories only (quality objectives are exempt from
PM003-PM005). PM004 flags a `so_that` whose tokens overlap `i_want` by
0.8 or more; the persona list and the implementation-noun deny list are
not built yet. PM005 accepts a Given/When/Then criterion or one starting
`free-form:`. PM006 currently checks only size, against `[pm]
max_story_points` (default 8, 0 disables). PM007 fires on a task whose
scope touches user-visible paths (anything outside docs, tests, tickets,
changelog.d, .github, notes, scripts and `*.md`) and whose parent is not
a story, unless it carries the `no-story` label.

## 3. Non-functional goals: quality objectives that must qualify

Not every goal has a user behind it (a 10x faster check, a flaky test
quarantine, a dependency upgrade). These are allowed, but they are a
second structured form, not an exemption from the first. A story has
`flavour = user_story | quality_objective`; a quality objective carries:

```toml
[objective]
attribute = "performance"            # closed list, declared in [pm.attributes]
driver    = "finding:PERF-check-median"   # a resolvable reference (section below)
metric    = "check_warm_full_ms"     # name registered in [pm.metrics] with a measurer
baseline  = { value = 220000, measured_at = "2026-09-23", by = "evidence:check_warm_full" }
target    = { op = "<=", value = 2000 }
verify    = "bench:check_warm_full"  # benchmark, test, or rule id that proves the target
```

What makes it qualify (and why it cannot be a loophole):

| Check | Rule | Refuses when |
|---|---|---|
| attribute is one of the declared quality attributes (performance, reliability, security, maintainability, observability, cost, compliance, developer-experience, and any the repo adds with a definition) | PM020 | free text, or an attribute with no definition |
| driver resolves | PM021 | the driver is evaluated at the transition out of `triage` and the resolved value is recorded in a `field` event; PM rules on terminal tickets read that event, never the current state (a fixed finding or a metric now inside its bound must not turn a closed ticket red). Refuses when `driver` is prose. Accepted shapes: `finding:<fingerprint>` (a current check finding), `ticket:<id>` (an incident or bug), `metric:<name>` (a series recorded in tracked evidence records whose value at the transition was outside a declared bound; never the per-machine `.frob/telemetry.jsonl`), `rule:<id>` (a ratcheted rule being tightened), `url:` (an external requirement) only together with one of the others |
| metric has a measurer | PM022 | the metric is not registered with a measurer the tool can run (a benchmark id, a `frob stats` series, a rule count, a test duration, a size in bytes). "Code quality" is not a metric; "LCOM4 of crate X" is |
| baseline is measured or honestly unmeasured | PM023 | missing; `unmeasured` is allowed only with `measure_with` naming the measurer, and the ticket cannot leave `triage` until the baseline is recorded by running it |
| target is checkable | PM024 | no operator or value, or a target already met by the baseline (nothing to do), or a target outside the metric's declared range |
| verify names a runnable proof | PM025 | not a benchmark, test, or rule id; at close the measurer is run under the same timeout contract as tests (`[pm] measurer_timeout_secs`) and the result must satisfy `target` or the close is refused with the measured value (this is the evidence binding of tickets.md section 6 applied to a number); `close` and `land` are outside the 100 ms mutation budget |
| the change does not alter user-visible behavior | PM026 | the ticket's landed diff changes a public symbol signature, a CLI flag, a config key, or an HTTP route, and no user story is linked. Detected from the gob-symbols public-API graph and the generated command and config metadata, never from grimble data; polarity P+ (a changed public symbol, flag, key or route is the offender); where the surface answer is Unknown in the diff (a re-export, or a language without a public-API adapter) the close guard reports one Unresolved on the ticket instead of passing; not declared; a quality objective that turns out to change behavior must gain a linked user story (`discovered-from`) before land |
| not boilerplate | PM027 | `driver` reason text or attribute definition matches the shared boilerplate list used for ack and waiver reasons, or the same objective text appears on more than `[pm] max_duplicate_objective_text` tickets |
| flavour is stable | PM028 | flavour changed after criteria or evidence exist; allowed only with a reason recorded in the `field` event and a return to `triage` |

Enablers and chores (dependency bump, rename, CI fix) that have no
user and no metric are type `chore`: they must be at or under
`[pm] max_chore_points`, must not change public surface (PM026 applies),
and must carry a parent epic or an `enabler-for` link to a story or
objective they unblock. A chore that fails either becomes a story or an
objective, by construction.

Portfolio balance: `[pm] max_objective_share` (default 0.4) warns when
quality objectives plus chores exceed that share of a cycle's committed
points (PM029), so the non-functional lane cannot quietly become the
whole plan; the cycle report shows the split.

## 4. Definition of ready, definition of done

Declared once, enforced at the transition that owns them:

```toml
[pm.ready]   # checked on -> ready, and by `doable`
require = ["story_or_objective_qualified", "criteria", "points", "scope", "parent"]
[pm.done]    # checked on close and land
require = ["criteria_evidenced", "objective_target_met", "docs_touched_or_excepted", "no_open_children", "changelog_fragment"]   # changelog_fragment evaluates REL003
```

`changelog_fragment` skips the ticket types in `[pm] changelog_exempt_types`
(default `epic` and `docs`; `[]` opts every type in).
`[pm] changelog_tests_only_types` (default `[]`, intended opt-in `["chore"]`) also
waives the fragment for a listed type when the ticket branch's diff against the base
touches only test files; an empty diff, any non-test file, or a missing branch does not
qualify, and a fragment the ticket carries is still validated.

Predicates are named Rust functions registered like rules; a repo
cannot add arbitrary code but can choose the set. `doable` only lists
tickets that satisfy `[pm.ready]`, so agents never pick an ill-formed
goal.

## 5. Cycles, capacity, and velocity

Milestone 2 or later (D36).

- A cycle is an object: `frob cycle new --start --end --goal`,
  with `capacity_points` either set or derived.
- Derived points: a ticket with pointed children is estimated by them. Its
  derived points are the sum of each child's effective points (a child's
  own derived points when it has pointed children, else its entered points);
  unpointed children add nothing and closed children still count. A story
  with no entered points is accepted by `frob cycle assign` with its derived
  points, shown as derived. Capacity counts leaves only: a member whose
  ancestor is also in the cycle is covered by that ancestor and counted as
  zero, so the same work is never counted twice. Entered points that differ
  from the children's sum are reported by `frob ticket doctor`
  (`E-DOCTOR-POINTS-ROLLUP`). `[pm] point_scale` picks the allowed entered
  values: `fibonacci` (default: 1, 2, 3, 5, 8, 13) or `integer` (any whole
  number from 1 to 255).
  <!-- frob:ticket 01M4FDAKV07ZFX861ZHJKMRAQ6 -->
- Every cycle date and state is judged by one clock in one zone: the UTC
  calendar day (`gob_time::Clock::today`, one clock per command), never the machine's local zone, so a run at
  00:06 UTC agrees everywhere. Tests do not pin the clock (no environment
  variable may change an outcome, docs/design/shared/architecture.md section 1.6); they build
  fixture dates relative to the UTC today instead.
- Velocity is measured from events: per cycle, the points of the
  tickets committed to that cycle (story, task, bug and chore with
  points; epics and milestones never count; PM029's committed points
  use the same set) that reached `done` in it. This is the same
  definition as the close-time ratio (one function, `commitment`), and a
  closed cycle's recorded ratio event is preferred over recomputing.
  Work finished in the window but never assigned to the cycle is
  reported separately as `unplanned_done` and never enters the ratio,
  the mean or capacity. `frob stats --section velocity [--last N]` prints the
  last N cycles, the rolling mean, and the standard deviation
  (`frob cycle velocity` remains as a hidden deprecated alias with the
  same numbers). `frob stats` (crate `frob-metrics`, pure functions over
  the fold) also reports points remaining by milestone and epic,
  throughput, cycle and lead time percentiles, and cost per point
  (a log-normal fit per cost unit); below `[pm] min_history` samples
  every figure is `unresolved` with the sample count.
  Carry-over leaves the cycle at close, so it counts in the completing
  cycle only.
- `frob cycle assign <ticket> <cycle>` refuses when committed points
  would exceed `capacity = rolling_mean - k * stddev` (`[pm] capacity_k`,
  default 0.5) unless `--over-commit --reason`; the reason is a `cycle`
  event (op `over-commit`) and shows on the cycle report. PM010 honors it:
  a commitment at or below the highest recorded over-commit is accepted and
  not flagged, and it fires again once the cycle grows past it. Bootstrap:
  until `[pm] min_history` (default 3) completed cycles exist, capacity is not
  enforced (PM010 is advisory) unless `capacity_points` is set, so a
  fresh repo never needs `--over-commit`. The rolling window is the last
  `max(6, min_history)` closed cycles and the stddev is the population
  one; the limit is floored to whole points. `assign` defaults the cycle to the
  open one holding today, else the next planned; a ticket lives in one open or
  planned cycle, so assigning it elsewhere moves it (`remove` then `add`);
  epics and unestimated tickets are refused. PM010 (advisory) flags an
  open or planned cycle committing more points than its capacity, silent
  while capacity is unenforced; PM011 (warn) flags such a cycle with no
  goal; PM012 (advisory) flags its not-yet-started members (triage or
  todo) that fail a `[pm] ready_requires` predicate, naming the failed
  ones. Closed cycles and started or finished members are not judged.
- Work comes from the sprint backlog. While a cycle is active and
  `[pm] sprint_gate` is true (the default), `frob work` and `start`
  refuse a ticket that is not a member of the active cycle with
  `E-PM-NOT-IN-CYCLE`; the hint names `frob cycle assign TICKET` and
  `--unplanned --reason TEXT`. Expedite tickets are exempt and with no
  active cycle the gate is silent. `frob work TICKET --unplanned --reason
  TEXT` assigns the ticket to the active cycle (leaving any other open or
  planned cycle) as an over-commit: a `member` event plus a `cycle` event
  (op `over-commit`) carrying the reason and no point totals, so unplanned
  work shows on the cycle report and in the retro. Only a ticket taking a
  fresh slot is judged; re-entering a ticket that already holds its
  lease is not. The overdue gate (PM036, section 8) runs first: an
  overdue cycle refuses before membership is looked at.
- `frob cycle plan [CYCLE] [--apply] [--points N]` proposes a commitment:
  the tickets `ticket doable` lists (so dependencies are respected), in its
  rank order (expedite, fixed-date by due, then the rest) except that
  tickets of the next milestone (the open one with the earliest target)
  lead the plain lane, until capacity. Each candidate goes through the same
  rules as `cycle assign`, so it never over-commits; it prints the picks
  (points, running total, why), the ready tickets already in the cycle and
  what it left out with the reason (no points, over the limit, in another
  cycle). Without an enforced capacity there is no limit to fill to, so it
  is refused (`E-CYCLE-NO-CAPACITY`) unless `--points N` gives one. By
  default nothing is written; `--apply` assigns the picks through the
  `assign` path and a repeat is a no-op.
- `frob cycle close` moves incomplete work to the next cycle with a
  `cycle` event (op `carried`), records the commitment-versus-done ratio, and
  refuses if any ticket in the cycle is in `in-progress` with a live
  lease (finish or requeue first).
  Storage: `carried` (ticket, to), `ratio` (committed and done points)
  and `retro` (text) are `cycle` events on the closing cycle; `carried`
  also takes the ticket out of that cycle's members while the target
  cycle gains it by a `member` event, so a closed cycle lists only what it
  finished. The target is the next open or planned cycle by start date, or
  `--carry-to`; with none, close refuses (E-CYCLE-NO-NEXT) and names `frob cycle new`
  and `--next-goal`. `frob cycle close CYCLE --next-goal TEXT [--next-days N]
  [--retro TEXT]` closes and, when unfinished members need a home and no next
  cycle exists, creates one starting the day after the effective end
  (`[pm] cycle_days` long unless `--next-days`) and carries them into it; its
  overlap check sees the closing cycle as closed at the effective end, and the
  ratio counts the carried tickets as committed. Write order, safe to retry:
  create the next cycle, add each carried ticket to it, then one commit on
  the closing cycle (carried, ratio, retro, transition); the cycle stays open
  until the last step, and a retry finds the created cycle as the next one.
  Cycles may share a date range once the earlier is closed: `cycle new`
  idempotency matches only open or planned cycles, and the later cycle's alias
  gets a numeric suffix (`2026-10-03..2026-10-04.2`; the first keeps the bare
  alias). The suffix is the cycle's stored `ordinal`, assigned once by the
  store at creation (one above the highest of its range) and carried by the
  `create` event, so aliases are unique by construction; `ticket doctor --fix`
  numbers legacy duplicates in creation order with a `field` event on
  `ordinal`. Handles, ULIDs and aliases resolve. A transition's `from` is
  judged against the state derived for the day of the event, not the stored one. Close events written before states were derived, which record `from = planned` on a day the cycle had started, are also accepted (legacy tolerance); any other mismatch is a conflict.
  Closing before the planned end records the close day (UTC, never before the
  start) as the cycle's effective end, in the `transition` event (`ended`);
  the fold sets `ended` on the cycle, and the overlap check, default-cycle
  selection, velocity, capacity, the ratio and the E-CYCLE-NO-NEXT suggested start
  all use the effective window. Closing on or after the planned end, or a close
  event without `ended`, leaves the planned end in force. `cycle show` and
  `list` report `end` (planned) and `ended` (effective, when different).
  `frob cycle new` ends at `start + [pm] cycle_days - 1` unless `--end`
  is given and refuses windows that overlap a cycle that is not closed.
- Agent capacity: throughput in points per day is measured the same way
  per agent identity, and pooled per identity class (human or agent)
  while an identity has fewer than `[pm] min_history` samples, because
  agent identities that change per session never accumulate their own;
  `wave --agents N` uses it to size waves.

## 6. Estimating time to deploy

Milestone 2 or later (D36).

Estimates are computed from measured history, never typed in:

- Per ticket type and size, the cycle-time distribution (ready to
  done) and lead-time distribution (created to landed) are derived
  from events.
- `frob forecast <milestone|epic|ticket>` runs a Monte Carlo over
  historical throughput and cycle times (10k trials) to give P50, P85,
  P95 completion dates, and the dominant risk (dependency chain,
  capacity, or unsized work). With fewer than `[pm] min_history`
  samples it reports Unresolved with the sample count instead of a date;
  it does not fall back to a capacity derived from the same missing
  history.
  Implemented in `frob-metrics::forecast` (seeded SplitMix64, bootstrap of
  the last 8 weeks of throughput and of cycle times; each trial finishes at
  the later of the capacity burn-down and the blocked-by chain). One
  function, `forecast_line`, renders the single line that `frob release
  status` and `frob ticket show` print; the standalone verb is not yet
  shipped.
- `frob ticket show` prints an ETA for a `ready` ticket from queue
  position, current WIP, and throughput (Little's law), with the
  inputs shown.
- Time to deploy = forecast of the last blocking ticket of the
  milestone plus the measured land-to-release lag; `frob release
  forecast` prints it with the critical path.
- Cost: tokens and wall-clock per story are measured from lease and
  harness events; cost per point is reported beside velocity so agent
  work is estimated in money, not hours.

## 7. Flow metrics and WIP

Milestone 2 or later (D36).

`frob stats` and the GUI dashboard: burndown and burnup per cycle and
milestone, cumulative flow by category, cycle-time scatter and
percentiles, flow efficiency (active versus blocked time from events),
aging WIP, throughput, and the commitment ratio. WIP limits are
enforceable; the knobs, defaults and what each refuses are the policy table in section 12 (D83), not repeated
here.

What counts toward WIP has one definition, `frob_pm::rules::wip::count`,
shared by the `work`/`start` gate and PM013: an in-progress ticket holds
a slot only while its lease is live (a ticket whose lease expired is
stale, named with a requeue hint but never counted); expedite tickets are
counted in their own lane, exempt from `in_progress` and capped by
`[pm.classes] expedite_max` (0 closes the lane, so expedite then counts
as standard). PM013 fires when live standard holders exceed
`in_progress` and when live expedite holders exceed `expedite_max`.

The repository-wide tables (`[pm]`, `[pm.wip]`, `[pm.classes]` and
`[lease]`) are read from `frob.toml` at the ledger ref (`[tickets] ref`),
not from the worktree copy, so a branch cut before a limit changed
enforces the current value; the worktree file is used only when the ref
has none. Per-worktree code config stays per worktree.

### Activity inference

The time of an in-progress ticket is classified from signals frob already
sees, never from a state an agent sets (`frob_metrics::activity`). Signals:
lease acquire and renew, worktree commit times, file mtimes when frob looks,
test and evidence runs, goway job reports, lease refusals (`E-LEASE-HELD`,
recorded as a local event against the refused ticket) and the land start and
end. `classify` sessionises them with an idle gap (default 15 minutes): a
point signal (commit, edit, lease) is implementing until the next signal,
for at most the gap, and the rest is idle; a refusal is waiting; test and
goway spans are testing; the land span is landing. The final point signal
contributes nothing.

The journal is local and never committed: one JSON-lines file per ticket in
`<git common dir>/frob/activity/<ticket ulid>.jsonl`, outside every work
tree, so nothing reaches the code branch. At land the totals per activity are
returned in the land outcome (`activity`) and, when the ledger lives on its own
branch, noted on the ticket as `activity: implementing 2h0m, testing 5m0s`.
<!-- frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W -->

## 8. Rule family PM (generated like every other family)

| Id | Checks |
|---|---|
| PM001-PM002 | milestone and epic completeness |
| PM003-PM006 | story structure, value statement, criteria shape, INVEST |
| PM007 | task without parent story |
| PM008 | ticket aging past `[pm.max_age_days]` per category (`in_progress` default 3, `ready` default 30, 0 is off); a ticket ages from its latest move into its category, epics do not age; there is no review category yet, so no review limit |
| PM009 | unsized ticket in `ready` (a non-epic in `todo` with no points) |
| PM010-PM012 | cycle over capacity, no goal, not-ready members |
| PM013 | WIP limit exceeded |
| PM014 | milestone without forecast (no sized work) or past target date |
| PM033 | replenish: ready work below `[pm] ready_min` (section 12) |
| PM034 | milestone member outside the milestone's epics (section 11) |
| PM035 | intangible-share: chores and debt above `[pm.classes] intangible_share` of a cycle's points (section 12) |
| PM036 | overdue cycle: a cycle still active after its end date (`today > end`, UTC); while it stands `frob work`/`start` refuse standard tickets with `E-PM-CYCLE-OVERDUE` (teaching message: close it with `frob cycle close --retro TEXT`); an expedite ticket still starts |
| PM037 | design obligation with no live implementing ticket (grimble/grmb-spec.md 16.5); fires only once some live ticket carries `implements`, so repos outside the planning join see nothing. Advisory severity is retired, so it is an Error. `frob plan --from-design --apply` creates the missing tickets (goal to epic, scenario to story, impl to task), idempotent per anchor; the `design_bound` close guard raises PM038 when a task implementing an impl whose `status_hi` is declared closes as done |
| PM039 | ticket closed `done` whose landed diff touches none of the identities bound to the entities it implements (grimble/grmb-spec.md 16.5); Warn is retired, so it is an Error. Silent when the entities have no bound identity or the host supplies no landed design facts (`PmHost::landed_design`) |
| PM015 | story done with zero evidenced criteria (should be unreachable; positive control) |
| PM020-PM029 | quality objectives: attribute, driver resolves, metric measurable, baseline, checkable target, runnable proof, no hidden behavior change, not boilerplate, stable flavour, portfolio share |
| PM030 | chore over `max_chore_points`, or with neither a parent epic nor an `enabler-for` link |
| PM037-PM049 | the grimble planning join, defined in grimble/grmb-spec.md 16.5: PM037-PM041, PM043, PM046-PM049 and the close guards `design_bound` (grimble/grmb-spec.md 17.5) and opt-in `design_verified` (PM047); PM042, PM044, PM045 unused; new PM ids start at PM050 |

All PM rules are Warn in a fresh repo and Error under
`[pm] strict = true`; `frob init --strict-pm` sets it (the composition
with `[check] strictness` is in docs/design/shared/rules.md section 7, and write-time
refusals follow it). Every `[pm]`
knob named in this file is materialized by `frob init` with its default
and doc comment (docs/design/shared/architecture.md section 1.6); none may be silently
inherited.

## 9. Agents and this discipline

Agents file follow-ups as `discovered-from` tasks into `triage`; a
human (or a triage rule) accepts them into a story. `brief` renders the
user story and criteria at the top so the prompt carries intent, and
`close` fails with the single missing predicate named. Nothing here
adds steps to the hot path: the structure is captured once at `new`,
and every later check is a read.

## 10. The design join (grmb planning entities)

Moved here from grimble/grmb-spec.md 17.2-17.6; the grmb spec keeps a pointer for each. Bare section numbers in this section (8.2, 12.8, 16.5 ...) are grimble/grmb-spec.md sections; 9.1-9.5 here were 17.2-17.6 there.

### 10.1 The canonical link

The ticket's `implements` link with a `design:` anchor
(`implements design:impl/web_app.checkout.system.shows_total`) is the one
link between a ticket and a planning entity; frob validates it against
`grimble graph --json` as for every grimble entity (tickets.md 3,
grimble/grmb-spec.md 21). A `frob:ticket` directive on a .grmb entity
(8.2) records provenance (which ticket changed that hunk) and is
never read as the link (D131): one source of truth.

### 10.2 Overlay and rollup

Per entity frob derives `planned` (a live ticket implements it),
`in-progress` and `done` (every live implementing ticket done, at least
one), plus the verdicts of 12.8 per evidence row (storing the entity's
`body_digest` on each record), and `verified` as 12.8 defines it. Goal progress is the rollup over its subtree; `grimble status`
shows bound and covered counts, `frob board` and the GUI the overlay and
burndown per goal (points of tickets implementing its entities).

### 10.3 Rules

PM037-PM039 and PM046-PM049 (16.5). Drift after done (a binding that empties after its
implementing ticket closed) is not a new rule: SYS004, SYS007 and SYS008
report it on the entity, and frob shows the implementing ticket next to
the finding.

### 10.4 Close guard `design_bound`

A named guard (tickets.md 3) in the default `[tickets.guards] close` set:
a ticket reaches `done` only if every planning entity it implements has
`status_hi` at least `bound` (an impl that binds nothing blocks its
ticket). If the two design statuses differ, or grimble is absent, the
guard is Unresolved, never a pass, and the close is refused with the
remedy to resolve the selector or close with another outcome. A
repository may remove it (it is not an integrity guard).

### 10.5 `frob plan --from-design`

A planner verb: reads `grimble graph --json`, proposes tickets, never
edits the model.

- Mapping: goal to `epic`; scenario to `story` (parent: the epic of its
  first realized goal); impl to `task` (parent: its scenario's story; a
  `for *` impl the first scenario's by name, `relates` to the others).
- Each ticket gets `implements design:<anchor>` and the anchor as its
  idempotency key, so a second run proposes only what is missing; scope is
  seeded from the realization and `verified_by` files (task) or the union
  of its children (story).
- Acceptance: a story gets one Given/When/Then per arm (given the path to
  the step, when it yields the variant, then the arm's terminal); a task
  gets "the realization selectors resolve and the `verified_by` tests pass".
- `requires` becomes `blocked-by` between the goals' epics; an includer's
  story is blocked by the included scenario's.
- Tickets are created unsized and unassigned (the scrum gates of
  pm-and-releases.md need points before `cycle assign`); the default output
  is the proposal, `--apply` writes through the ledger.
- `--findings` turns each MDL022, MDL023 and SYS015 finding into a task
  that implements the scenario and `fixes` the finding fingerprint: a new
  variant becomes backlog.

## 11. Vocabulary (one meaning each)

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
  (section 5), not a release. Cycles are optional: scrumban
  runs on flow, and cycles give it a heartbeat.
- **Release = cutting a milestone.** It happens when the milestone is
  ready, not when a cycle ends.

## 12. Scrumban policies (explicit, materialized in `[pm]`)

Scrumban takes Kanban's flow (visualize, limit work in progress, pull,
explicit policies, measure) and keeps Scrum's useful cadences. Each
policy below is a materialized knob, so a repository can see and change
its own process.

| Policy | Knob (default) | Enforced by |
|---|---|---|
| **Pull, ranked.** Work is taken from `frob ticket doable`, highest rank first; nobody is assigned work they did not pull. | `[pm] pull = "rank"` | `work` and `start` take the ticket; `doable` orders it |
| **WIP limit per holder.** One ticket in progress per holder (actor plus worktree path, so parallel agents in separate worktrees are not one identity), so an agent finishes before starting. | `[pm.wip] in_progress_per_identity = 1` (0 turns it off) | `start` refuses a second (v1 T-5718) |
| **WIP limit for the repository.** The number of in-progress tickets is capped at what the machine can build. In this repository that is two, the disk rule (frob-v2-disk-guard). A category limit makes the board column red and PM013 fire. | `[pm.wip] in_progress = 2` | PM013; `work` refuses past the limit, naming the holders |
| **Replenishment order point.** When ready work falls below a threshold, planning happens then, on demand, not on a calendar. | `[pm] ready_min = 4` (twice the WIP limit) | PM033 replenish (Advisory): "ready queue is 1, below 4: run frob cycle plan or triage" |
| **Classes of service.** `expedite` (a critical bug or security issue: may exceed the repository WIP limit by one, at most one at a time); `fixed-date` (ranked by due date); `standard`; `intangible` (chores and debt, capped as a share of each cycle's points). | `[pm.classes] expedite_max = 1`, `intangible_share = 0.2` | PM013 counts expedite separately; PM035 intangible-share checks the share |
| **Definition of ready.** A ticket enters `ready` only with scope, acceptance and points. | `[pm] ready_requires` | PM012, PM005 |
| **Definition of done.** Close guards: criteria evidenced, docs touched or excepted, no open children, changelog fragment. | `[pm] done_requires` (section 4) | the close guard, REL003 |
| **Cadences.** Replenishment on demand (order point); cycle review at each cycle close (commitment ratio, flow metrics, one retro note event); release on demand when a milestone is ready; a dev build on every green land. | `[pm] cycle_days = 7` | `frob cycle close`, `frob release status` |
| **Bucket planning.** Only the next milestone is planned in detail; later ones keep a goal and epics and stay `unscheduled` until `frob forecast` has the history to date them. | none | PM001 allows `unscheduled` |

## 13. Every land keeps main releasable

Incremental releases depend on main always being shippable:

- The land gate (`frob check`) and whole-workspace evidence already hold
  for every land.
- Every user-visible change carries a changelog fragment
  (`changelog.d/<ulid>.<type>.md`, REL003 at close), so release notes
  are ready at all times and no one writes them at release time.
- A ticket's milestone is set when it is planned. `frob release status`
  shows what a cut would contain at any moment.

## 14. Verbs

| Verb | What it does |
|---|---|
| `frob milestone new VERSION --goal "..." [--target DATE]` | creates the release object; exit criteria are added as `--criterion` and bound to evidence like acceptance |
| `frob milestone add EPIC VERSION` | adds an epic; tickets join through their epic (PM034 keeps it that way) |
| `frob milestone criterion add VERSION TEXT` / `remove VERSION N` | edits the exit criteria; a removal records the `moved` map (old position to new, 0 when removed) so evidence follows its criterion |
| `frob milestone evidence add VERSION --provider P --ref R [--accepts N]...` / `list VERSION` | captures a record with the same providers, allowlist and format as `ticket evidence add` and offers it for exit criteria; `milestone show` prints each criterion as `bound` or `unbound` with the binding evidence (latest record per provider, ref and criterion decides; only measured, passing records bind; `--provider attestation --statement T [--fact F]...` is a listed attester's statement for criteria no tool measures, shown as `attested`, shared/security.md 2.3). `milestone criterion remove` reports the evidence that loses its criterion (`lost_evidence`, as `ticket update` does) |
| `frob release status [VERSION]` | readiness: every exit criterion evidenced; no open ticket in the milestone's epics; CI green on the tip; fragments compile; GEN001 and the pack lock clean. It also prints what is left, the forecast for it (section 6) and the changelog preview. It never fails a check; it reports. |
| `frob release cut VERSION` | requires status ready (or `--override --reason`, recorded as an event). Bumps the lockstep version of every crate (shared/charter.md 4); compiles CHANGELOG.md from the fragments and removes them; commits on main through the land machinery (CAS, one commit); tags one tag per configured product (section 15). Pushing the tag starts the release job. As built: `frob release cut VERSION [--override --reason TEXT] [--push]` refuses a dirty tree, a checkout off the base branch, an existing tag and a not-ready status (exit 3 with the remedy); the override reason is a `override` event on the milestone; the commit is `chore(release): cut VERSION`; tags are annotated, local unless `--push`, one per `[release] products` entry named by `[release] tag` (this repository: `frob-v` and `grimble-v` tags); the milestone gets a `cut` event (version, commit, tag names and oids; REL001 reads it) and moves to `released`. A failure after the commit resumes by re-running the same command (failure matrix in `crates/frob-release/src/cut.rs`). |
| `frob release adopt VERSION [--reason TEXT]` | records tags made by hand as the version's cut, so a published tag is never deleted to satisfy REL001. It resolves the tags the configured `[release] tag` pattern and `products` name for VERSION, checks each exists and peels to a commit (annotated or lightweight), and appends the `cut` event `release cut` writes (version, commit, tag names and oids) followed by an `adopt` event (version, optional reason; the actor is the event envelope's), then moves the version's milestone to `released`; with no milestone it creates one, already released, because cut events live in a milestone's log. The marker is a separate event kind rather than a field of `cut` because `CutData` denies unknown fields: an older binary reads the unknown kind as `other` and the `cut` event unchanged, so it keeps working on the ledger (and still treats the tag as cut). Never writes a ref or touches the remote; idempotent (a repeat returns `already`); a missing tag is `E-ADOPT-NO-TAG`, one that is not a commit `E-ADOPT-NOT-COMMIT`. REL001's remedy names it first |
| `frob release notes --version X` | prints the body of that version's CHANGELOG.md section (heading and integrity marker removed) as `data.notes`, and with `--text` the section alone, raw, with no envelope; the release job feeds it to `gh release create --notes-file` via `--text > notes.md` (the linux archive's own binary, no markdown parsed and no jq in shell) and does not use `--generate-notes`, so the compiled section is the whole release body. It reuses `changelog::split` and `heading_version`; a missing section is `E-CHANGELOG-NO-SECTION` |
| `frob release bump VERSION [--dry-run] [--allow-downgrade]` | sets the one lockstep version: `[workspace.package] version` (added when absent), every member made to inherit it with `version.workspace = true` (one line to edit per release, no member can drift), the `version` of intra-workspace path dependencies, a static wheel `pyproject.toml` version, then `Cargo.lock` through an offline `cargo update --workspace`; format-preserving, idempotent (a repeat reports `already`), refuses a version below the current one without `--allow-downgrade`, and re-runs REL002 afterwards. `release cut` calls it |
| `frob release forecast VERSION` | time to release: the forecast of the last blocking ticket plus the measured land-to-release lag |
| `frob cycle new/plan/assign/close/velocity` | as section 5; `plan` fills to capacity from ready work in rank order, preferring the next milestone |
| `frob board` | the scrumban board: columns by category, WIP limits shown, expedite lane, aging per card. As built: `frob board [--width N] [--cards N]`; columns triage, todo (`doable` order first), in-progress, blocked (a todo ticket with an open blocker; in-progress tickets stay in their column so the count matches PM013) and done (last 7 days); epics are left off. The in-progress header is `count/limit` from the one WIP count (`frob_pm::rules::wip::read`, shared with PM013 and `work`), so stale holders are marked `STALE` and not counted, and an exceeded limit shows `!` (red with color). The expedite lane, when `[pm.classes] expedite_max` is above 0, lists every live expedite ticket on top. Each card shows handle, points, age (since the ticket entered its current category, from `transition` events: `<1m`, `5m`, `7h`, `3d`), title, lease holder and due date. Text is ASCII, sized to `--width`, else `COLUMNS` on a terminal, else 100 (stacked below 16 characters per column); `--json` carries the same typed board in `data.board`; `--brief` (D104/D105) is the compact view of the same board: NOW (in-progress with holder, worktree, age and last observed signal and its time since, inferred from the lease heartbeat, commits on the ticket branch, and evidence, land and move events, never declared), NEXT (doable order) and BLOCKED (with open blockers), in `data.brief` under `--json`; other columns list at most `--cards` (default 8) cards and count the rest. |

New rules: **PM033 replenish** (Advisory, the order point), **PM034
milestone-member-outside-epics** (Warning, the v1 T-5149 failure),
**REL001 release-without-cut** (Error: a product tag, per the configured tag pattern, not made by
`release cut`, so versions, changelog and tags never disagree), and
**REL002 lockstep-version-mismatch** (Error: workspace crates whose
versions differ). REL001 was v1's debt rule; its id is reused only
because shared/rules.md 6 retired the v1 meaning, and the rule page says
so.

## 15. Products, tag pattern and the changelog in any repository

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

The date of a compiled changelog section is the UTC calendar day of the command's clock (`--date` overrides it), never the machine's local zone, so a cut at 00:06 UTC is dated the same everywhere (shared/architecture.md, D93).

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

## 16. Channels and version scheme

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
number (shared/charter.md 4). Under 0.x semver no stability is promised, and
installing or upgrading `frob` after 0.532.0 gives the rewrite: the
0.532.0 release notes say so plainly, with the v1-to-v2 differences and
how to pin 0.531.0.

## 17. The release job (lessons carried from v1)

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
  shared/charter.md 6), named after the dist package: `frob-cli-<target>.tar.xz`
  (`.zip` on windows) holding `frob`, and `grimble-<target>` holding
  `grimble`, each with a `.sha256`; crunk joins as one more entry,
  `crunk-<target>`. cargo-dist 0.32 names an archive after its package
  and has no rename option, so the frob archive keeps the `frob-cli`
  package name (the crates.io name, shared/charter.md 6). `dist-workspace.toml`
  sets `dist = false` as the workspace default and each product package
  opts in with `[package.metadata.dist] dist = true`; no published crate
  declares a binary that is not a product (test helpers such as
  `fake-sibling` live in the `publish = false` crate `gob-testsupport`).
  `crates/frob-release/tests/it/products.rs` pins the binary set, the dist
  set and the archive names the smoke and upload steps use.
- **Build matrix:** cargo-dist per binary (shared/charter.md 4): linux
  x86_64 and aarch64, macOS arm64 and x86_64 (cross), windows x86_64.
  PyPI gets one wheel set per product, each carrying only its own
  binary; `frob` depends on `grimble` and `crunk` at the same version
  (shared/charter.md 6, D87). As built, `packaging/pypi/products.toml` is the
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
  shared/security.md's CI rules apply. Every crate publishes (`publish` is set
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

## 18. Details (closing the 0.532.0 planner's gaps)

- **Storage of milestones and cycles.** They are ledger objects with the
  same event-sourced storage as tickets: an object directory holding a
  frontmatter file folded from its own events, identified by a ULID,
  with the version (milestones) or the dates (cycles) as aliases. Kinds
  `milestone` and `cycle` join tickets.md 2.4 (`create`, `field`,
  `member` for epic and ticket membership, `criterion`, `transition`).
  In the milestone-1 layout they live at `tickets/_milestones/<ULID>/`
  and `tickets/_cycles/<ULID>/`; on the ticket branch at `_milestones/`
  and `_cycles/` (shared/documentation.md 3.1). Membership is an event on the
  object, never a field on the ticket, so moving a ticket between
  cycles is one append.
- **One version, per-product tags.** Every crate and the wheel carry one
  lockstep version (section 16); `release cut` tags each configured product
  at the same commit (section 15; shared/charter.md 4, updated). Here that is
  `frob-vVERSION` and `grimble-vVERSION`, plus `crunk-v` once it exists.
- **Forecast in `release status`.** Printed only when `[pm] min_history`
  cycles exist; before that the line is Unresolved with the sample
  count. The line comes from `frob-metrics::forecast::forecast_line`, the
  same function `ticket show` uses. `frob release forecast` ships with
  0.536.0.
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
- **Dev channel branch.** "main" in section 16 means the repository's
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
  nothing to PyPI or crates.io. CI cost controls (~BN7DCP3): superseded
  runs are cancelled per job (`<workflow>-<ref>-<job>` groups, never a
  workflow-level group, which would also cancel a `dev-publish`
  mid-upload); a `changes` job skips the Rust jobs for pushes that touch
  only tickets, changelog fragments, notes and the design, decision and
  migration docs (a job-level filter, not a `paths:` trigger, so every
  commit still carries checks for the land gate); a `dev-gate` job
  rebuilds the dev channel at most once an hour, so the last land of a
  burst can wait for the next code push to be published; and sccache
  (GitHub Actions backend) caches workspace crates by content across
  runs. `crates/frob-release/tests/it/dev_workflow.rs`
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
- **Release-tier findings in `release status`.** When `crunk.toml` exists,
  `crunk check --gate release --json` runs (sibling lookup, 300 s cap) and
  every HUMAN error finding (a stale human review, D120 area) becomes a
  `release-tier` blocker, so `release cut` refuses without `--override
  --reason`. A gate that cannot run or print JSON is an Unresolved line
  ("release-tier findings"), never a silent pass; no `crunk.toml` is not
  applicable.
- **Owner actions before the first publish.** Configure trusted
  publishing on PyPI (`frob`) and, once the first publish has created the
  crates, on crates.io (the first publish uses a token in the release
  environment); confirm ownership of the reserved
  crate names (shared/charter.md 5). These are human steps, listed by
  `frob release status` as Unresolved items until done.
- **Rule numbers.** PM035 intangible-share (Warning) is new; PM014 keeps
  its pm-and-releases.md meaning (milestone without forecast). PM010 to
  PM012 and PM035 are not in 0.532.0 (cycles ship at minimum scope).

## 19. The v2 milestone list

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
(bucket planning, section 12).

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D17

Project management is enforced: structured stories, ready/done definitions, capacity-checked cycles, Monte Carlo forecasts from events

### D19

Non-functional goals are quality objectives with a resolvable driver, a registered metric, a measured baseline, a checkable target and a runnable proof; a graph-detected public-surface change forces a user story

### D105

Owner decisions 2026-10-06: human-readable views are text renderings of the same JSON (`board --brief`, `ticket list --tree` as the backlog, `stats`); metrics are computed in a new crate frob-metrics (velocity, capacity, cost per point as a log-normal model fitted on the log scale with median and P85, Monte Carlo forecasts, activity inferred from observed signals, never declared by agents); the live dashboard is a separate binary frob-live (ratatui) shipped in the frob wheel and reached by `--live` on board and stats, so frob itself links no TUI; activity telemetry is a local .frob journal summarised onto the ticket branch, never code-branch commits


### D83

Releases (~5MAFAAY): milestone = version (a release object with goal, exit criteria and epics), cycle = optional time box; scrumban policies as materialized knobs (pull by rank, WIP per holder 1 and per repository 2, replenishment order point PM033, classes of service, definitions of ready and done, on-demand cadences, bucket planning); every land keeps main releasable (fragments at close); `milestone`, `release status/cut/forecast`, `cycle`, `board` verbs; PM033-034, REL001-002; channels dev/alpha/stable; v1 release-job lessons; the v2 milestone list 0.532.0 to 0.536.0; version scheme (owner 2026-10-03): v2 continues the PyPI line as 0.53X.0 in lockstep across crates.io and PyPI, and 1.0.0 is the first stable version

### D90

Owner decisions 2026-10-04 for crunk in the monorepo (planner defaults accepted): milestones 0.537.0 (crunk core, preview, Python crunk retired) and 0.538.0 (crunk-web, gallery, grimble-websec and grimble-sysdesign); CSS declarations and at-rules join the universal model U rather than a crunk-private form; crunk's value rules (color, contrast, units) are Rust until GRL gains value built-ins; fix application lives in a shared gob-fix crate, gob-rules records only fix applicability; crunk-web and the gallery are opt-in (the gallery a cargo feature off by default, on gob-serve); the four mixed web-app v1 tickets import under grimble

### D135

Owner decision 2026-10-09, supersedes the D87 hold-back (and the D90 timing that retired the Python crunk at 0.537.0): from 0.533.0 `release.yml` uploads the five Rust crunk wheels to the PyPI project `crunk` together with `frob` and `grimble`, replacing the Python crunk (lognd/crunk, 0.1.x); the hold-back step is removed; the PyPI `crunk` project trusts this repository's `release.yml` with environment `pypi` (set up by the owner); trigger: frob 0.532.0's crunk sibling call fails against PyPI crunk 0.1.1 (hullbreach gap 5); the rest of D87 stands (one binary per package, `frob` still depends on `grimble` only)

Also logged against: packaging/pypi/BUILDING.md.
