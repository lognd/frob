# Time: one clock, one zone, from type to lint (D93)

Status: draft
Owner: gob
Decisions: D93, D86
Audience: contributor

Provenance: section 5 step 1 built (gob-time, one pinned clock in the command context, clippy
confinement); steps 2 and 3 follow. Accepted direction, owner request 2026-10-04 ("Can we add a time
lint?"). ~AAZFNR5 turned CI red at 00:06 UTC: `frob cycle` derived a
cycle's state from the UTC day while the library's `Day::today()` used
the machine's local zone, and the cycle tests hardcoded a "future" date
that became today. Each piece compiled and passed on most runs. As with
paths (D86, paths.md), a lint alone finds some of this after it is
written; this design makes the wrong thing hard to write in this
repository, and ships the TIME lint family (rules.md 3.2) as the second
line and as the product feature for other repositories.

## 1. Four kinds of time, four types

| Kind | Type | Zone | Where it lives |
|---|---|---|---|
| Elapsed time: how long something took | `std::time::Instant`, `Duration` | none | timing, timeouts, backoff; never persisted, never compared across processes |
| Instant: when something happened | `gob_time::Stamp` (UTC, RFC 3339 with `Z`) | UTC | everything persisted or compared: ledger events, leases, evidence, caches, snooze `until` |
| Calendar day: which day something belongs to | `gob_time::Day` | UTC by contract (pm-enforcement.md section 4) | cycles, due dates, release section dates, velocity windows |
| Display time: text for a person | `gob_time::Shown` (render-only) | the user's local zone | the rendering layer only |

`Stamp` and `Day` move to a new leaf crate, `gob-time` (today `Stamp`
lives with the ledger and `Day` in frob-pm), and become the one
instant type and the one day type for every crate. A local-zone value
never enters data; `Shown` is the only conversion to local time, and it
only produces text.

## 2. One clock, read once per command

`gob_time::Clock` is a trait with `now() -> Stamp` and `today() -> Day`
(`today` is derived from `now`, never read separately).
`SystemClock` reads the system time; `FixedClock` returns a set
instant. A verb receives its clock from the command context and reads
it once: every date a single command computes or writes comes from one
snapshot, so a command that runs across midnight cannot disagree with
itself. Library code takes `&dyn Clock` (or a `Stamp` it was given);
it never reads the system time.

There is no environment variable or hidden flag that overrides the
clock: architecture.md section 6 forbids environment that changes an
outcome. Library tests use `FixedClock`. CLI tests never hardcode a
calendar date that is meant to be in the past or future: they build
dates relative to the clock's day (the helpers ~AAZFNR5 introduced),
and a test that needs an exact date (a boundary like 00:06 UTC) is a
library test with `FixedClock`.

## 3. Compile-time confinement

`clippy.toml` `disallowed-methods` forbids reading the wall clock
outside `gob-time`: `std::time::SystemTime::now`,
`std::time::SystemTime::elapsed`, `jiff::Timestamp::now`, `jiff::Zoned::now`
and the local-zone constructors (`jiff::tz::TimeZone::system`, `try_system`;
jiff has no civil `Date::today`). The lint is `deny` in the workspace.
`std::time::Instant::now` stays allowed (elapsed time is not a date).
`gob-time` carries the one `#[allow]` with a reason (`src/wall.rs`, the only file that reads the wall clock). As built, the command
context holds one `SystemClock::pin()` snapshot (`Context::clock`), `Ledger`, `LeaseStore` and `Workspace` take the
clock at open, and `Cache` defaults to `SystemClock` (rows are dated, never compared) until `with_clock` replaces it. A crate that needs
the time takes a `Clock`.

## 4. The lint family (product feature)

TIME is a grimble family (owner grimble, crate grimble-lints, universal
over U like PATH); rules.md 3.2 has the table. In short: TIME001 flags a
local-zone or naive current-time read whose value is stored, compared
or sent (Python `datetime.now()` without `tz`, `date.today()`,
`datetime.utcnow()`; JS `new Date()` formatted with local getters;
Rust `Zoned::now`, `chrono::Local::now`); TIME002 flags arithmetic or
comparison between a naive and an aware datetime; TIME003 flags a test
that builds or asserts a calendar date literal while the code it reaches
reads the wall clock with no clock injected, the exact shape of
~AAZFNR5. Where the call graph cannot decide reach, TIME003 is
Unresolved, never clean.

## 5. Sequencing

1. `gob-time` with `Stamp`, `Day`, `Shown`, `Clock`, `SystemClock`,
   `FixedClock`; migrate every wall-clock read; clippy confinement.
2. TIME001 and TIME002 in grimble-lints for Rust and Python.
3. TIME003 on the call graph, with its fidelity row.
