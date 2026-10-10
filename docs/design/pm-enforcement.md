# Enforcing project management

Status: current
Owner: frob
Decisions: D36
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-01: enforce good
project-management practice, not just record it: structured user
stories for functional goals, velocity-aware cycle commitments, and
real estimates of time to deploy.

Milestone 2 or later (D36): cycles, capacity, forecasts, flow metrics and
the PM rule family; milestone 1 keeps only the optional story fields of
section 2.

## 1. The hierarchy and what each level must carry

| Level | Required before it can leave `triage` | Enforced by |
|---|---|---|
| milestone (a release object, not a ticket type) | goal statement, target date or `unscheduled`, at least one epic | PM001 |
| epic | outcome statement, success metric, milestone | PM002 |
| story (functional goal) | a structured user story (section 2), acceptance criteria in Given/When/Then, size, parent epic | PM003-PM006 |
| story (quality objective) | attribute, resolvable driver, registered metric, baseline, target, runnable proof (section 2a) | PM020-PM029 |
| chore | small, no public-surface change, an `enabler-for` link or a parent epic | PM026, PM030 |
| task, bug, chore | parent story or an explicit `no-story reason` (bugs and chores may stand alone; a task with user-visible behavior may not) | PM007 |

Every field is checked at write time by the verb and again by the PM
rule family (crate `frob-pm`) in `frob check`, so a hand-edited or
migrated ticket is caught too. A write-time refusal follows the severity
of the rule: the verb refuses (with the exact remedy) only when the
rule's effective severity is Error, and otherwise succeeds with the
finding as a warning in the envelope (rules.md section 7 composes the
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

## 2a. Non-functional goals: quality objectives that must qualify

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
| verify names a runnable proof | PM025 | not a benchmark, test, or rule id; at close the measurer is run under the same timeout contract as tests (`[pm] measurer_timeout_secs`) and the result must satisfy `target` or the close is refused with the measured value (this is the evidence binding of tickets.md section 9 applied to a number); `close` and `land` are outside the 100 ms mutation budget |
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

## 3. Definition of ready, definition of done

Declared once, enforced at the transition that owns them:

```toml
[pm.ready]   # checked on -> ready, and by `doable`
require = ["story_or_objective_qualified", "criteria", "points", "scope", "parent"]
[pm.done]    # checked on close and land
require = ["criteria_evidenced", "objective_target_met", "docs_touched_or_excepted", "no_open_children", "changelog_fragment"]   # changelog_fragment evaluates REL003
```

Predicates are named Rust functions registered like rules; a repo
cannot add arbitrary code but can choose the set. `doable` only lists
tickets that satisfy `[pm.ready]`, so agents never pick an ill-formed
goal.

## 4. Cycles, capacity, and velocity

Milestone 2 or later (D36).

- A cycle is an object: `frob cycle new --start --end --goal`,
  with `capacity_points` either set or derived.
- Every cycle date and state is judged by one clock in one zone: the UTC
  calendar day (`gob_time::Clock::today`, one clock per command), never the machine's local zone, so a run at
  00:06 UTC agrees everywhere. Tests do not pin the clock (no environment
  variable may change an outcome, architecture.md section 6); they build
  fixture dates relative to the UTC today instead.
- Velocity is measured from events: per cycle, the points of the
  tickets committed to that cycle (story, task, bug and chore with
  points; epics and milestones never count; PM029's committed points
  use the same set) that reached `done` in it. This is the same
  definition as the close-time ratio (one function, `commitment`), and a
  closed cycle's recorded ratio event is preferred over recomputing.
  Work finished in the window but never assigned to the cycle is
  reported separately as `unplanned_done` and never enters the ratio,
  the mean or capacity. `frob cycle velocity [--last N]` prints the
  last N cycles, the rolling mean, and the standard deviation.
  Carry-over leaves the cycle at close, so it counts in the completing
  cycle only.
- `frob cycle assign <ticket> <cycle>` refuses when committed points
  would exceed `capacity = rolling_mean - k * stddev` (`[pm] capacity_k`,
  default 0.5) unless `--over-commit --reason`; the reason is a `cycle`
  event (op `over-commit`) and shows on the cycle report. Bootstrap:
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
  lease is not. The overdue gate (PM036, section 7) runs first: an
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

## 5. Estimating time to deploy

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
- `frob ticket show` prints an ETA for a `ready` ticket from queue
  position, current WIP, and throughput (Little's law), with the
  inputs shown.
- Time to deploy = forecast of the last blocking ticket of the
  milestone plus the measured land-to-release lag; `frob release
  forecast` prints it with the critical path.
- Cost: tokens and wall-clock per story are measured from lease and
  harness events; cost per point is reported beside velocity so agent
  work is estimated in money, not hours.

## 6. Flow metrics and WIP

Milestone 2 or later (D36).

`frob stats` and the GUI dashboard: burndown and burnup per cycle and
milestone, cumulative flow by category, cycle-time scatter and
percentiles, flow efficiency (active versus blocked time from events),
aging WIP, throughput, and the commitment ratio. WIP limits are
enforceable, with defaults and policy in releases.md 2 (D83):
`[pm.wip] in_progress_per_identity` (default 1; 0 turns it off) makes
`start` refuse a second concurrent ticket for one holder (actor plus
worktree path, so parallel agents in separate worktrees are not one
identity); `[pm.wip] in_progress` (default 2) caps the repository; a
category limit makes the board column red and PM013 fire.

What counts toward WIP has one definition, `frob_pm::rules::wip::count`,
shared by the `work`/`start` gate and PM013: an in-progress ticket holds
a slot only while its lease is live (a ticket whose lease expired is
stale, named with a requeue hint but never counted); expedite tickets are
counted in their own lane, exempt from `in_progress` and capped by
`[pm.classes] expedite_max` (0 closes the lane, so expedite then counts
as standard). PM013 fires when live standard holders exceed
`in_progress` and when live expedite holders exceed `expedite_max`.

## 7. Rule family PM (generated like every other family)

| Id | Checks |
|---|---|
| PM001-PM002 | milestone and epic completeness |
| PM003-PM006 | story structure, value statement, criteria shape, INVEST |
| PM007 | task without parent story |
| PM008 | ticket aging past `[pm] max_age_days` per category |
| PM009 | unsized ticket in `ready` |
| PM010-PM012 | cycle over capacity, no goal, not-ready members |
| PM013 | WIP limit exceeded |
| PM014 | milestone without forecast (no sized work) or past target date |
| PM033 | replenish: ready work below `[pm] ready_min` (releases.md 2) |
| PM034 | milestone member outside the milestone's epics (releases.md 1) |
| PM035 | intangible-share: chores and debt above `[pm.classes] intangible_share` of a cycle's points (releases.md 2) |
| PM036 | overdue cycle: a cycle still active after its end date (`today > end`, UTC); while it stands `frob work`/`start` refuse standard tickets with `E-PM-CYCLE-OVERDUE` (teaching message: close it with `frob cycle close --retro TEXT`); an expedite ticket still starts |
| PM015 | story done with zero evidenced criteria (should be unreachable; positive control) |
| PM020-PM029 | quality objectives: attribute, driver resolves, metric measurable, baseline, checkable target, runnable proof, no hidden behavior change, not boilerplate, stable flavour, portfolio share |
| PM030 | chore over `max_chore_points`, or with neither a parent epic nor an `enabler-for` link |

All PM rules are Warn in a fresh repo and Error under
`[pm] strict = true`; `frob init --strict-pm` sets it (the composition
with `[check] strictness` is in rules.md section 7, and write-time
refusals follow it). Every `[pm]`
knob named in this file is materialized by `frob init` with its default
and doc comment (architecture.md section 6); none may be silently
inherited.

## 8. Agents and this discipline

Agents file follow-ups as `discovered-from` tasks into `triage`; a
human (or a triage rule) accepts them into a story. `brief` renders the
user story and criteria at the top so the prompt carries intent, and
`close` fails with the single missing predicate named. Nothing here
adds steps to the hot path: the structure is captured once at `new`,
and every later check is a read.
