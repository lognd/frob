# Output: pretty TTY presentation, stage events and logging

Status: draft
Owner: frob
Decisions: none
Audience: contributor

Provenance: design for epic ~E2QBC17 (owner request 2026-10-26), ticket
~BAYVPRM. Modelled on lognd/clocx (ratatui 0.30, anstyle 1, tracing and
tracing-subscriber). This file is the contract the follow-up tickets
build against; it changes no code.

## 1. Goal and invariants

On a terminal every frob verb prints coloured, aligned output, and long
verbs (`land`, `check`, `work`, `test`) show a progress bar or spinner
with per-stage timings. Everything else stays as it is:

1. The JSON envelope (cli.md) is unchanged byte for byte. Presentation
   is a view over the same envelope and never adds a fact absent from
   JSON (cli.md, output selection).
2. Decoration is opt-out by environment, never by flag guesswork: a
   non-TTY, `NO_COLOR`, `TERM=dumb` or CI each switch it off (section 3).
3. All human output goes through the logging layer (gob-log). Verb code
   never calls `println!`, `eprintln!`, `print!` or `dbg!` (ban:
   ~J1PTXPF clippy deny, ~4270F1C routing).
4. Stdout carries the verb result only; stderr carries progress,
   spinner and log events. A pipe on either side never receives escape
   sequences.

## 2. Crate boundary

A new crate `crates/frob-present` (product: frob; depends on `gob-log`,
`gob-diagnostics`, `anstyle`, `ratatui`, `tracing`; no dependency on
verb crates, so verbs depend on it, never the reverse).

| Owns | Does not own |
|---|---|
| `Palette` (anstyle styles by semantic role) | verb logic and envelope construction (frob, gob-cli) |
| `Capabilities` detection (TTY, colour, width, CI) | the tracing subscriber install (gob-log `init`) |
| `Presenter` trait and its three implementations | diagnostics snippets (gob-diagnostics renders; present styles) |
| `StageEvent` model and the progress/spinner widgets | timing measurement (producers in frob-land, frob-check) |
| `ProfileReport` rendering | the clock (gob-time `Clock`, injected) |
| table, status line and error layout helpers | redaction (gob-log `redact`, applied before styling) |

gob-log gains one extension point rather than a second sink: a
`tracing` layer, `PresentLayer`, registered by `init` when
`Capabilities.interactive` is true. It receives events carrying the
field `ui = true` (the human-facing ones) and hands them to the active
`Presenter`. Plain diagnostic events (no `ui` field) keep the existing
stderr fmt layer and `FROB_LOG` filtering, so logging and presentation
do not fight over the terminal: while a bar is active the fmt layer
writes through the presenter's `suspend` so lines scroll above the bar.

## 3. Detection

`Capabilities::detect(env, streams)` is a pure function over an injected
environment snapshot and stream facts (testable without a terminal).

| Input | Rule |
|---|---|
| stdout/stderr TTY | `std::io::IsTerminal`, per stream, independently |
| `NO_COLOR` set and non-empty | colour off (no-color.org); layout and progress may stay |
| `CLICOLOR_FORCE` / `FORCE_COLOR` non-zero | colour on even when not a TTY (opt-in only; never affects JSON) |
| `TERM` unset on unix, or `dumb` | colour off, no cursor control, no spinner redraw |
| `CI` set (any value but `0`/`false`) | colour per the above, but progress degrades to one plain line per stage start and end, no redraw |
| `--format json` (or auto with stdout not a TTY) | stdout is the envelope; the presenter is `Quiet` for stdout |
| `--text` | forces the text view on stdout; colour still follows the rules above |
| `--quiet` | `Quiet` presenter, errors only |

Derived flags: `color` (stream is TTY, or forced, and not suppressed),
`interactive` (stderr TTY and not dumb and not CI: may redraw), `width`
(from `crossterm::terminal::size`, fallback `COLUMNS`, fallback 80).

Edge cases and decisions:

- Piped stderr with TTY stdout (`frob land 2>log`): stdout text is
  coloured, stderr is plain lines, no bar. Streams are judged separately.
- Piped stdout with TTY stderr (`frob check | jq`): the envelope goes to
  stdout, the bar still draws on stderr. This is the common agent and
  script case and must not corrupt the pipe.
- Windows: ANSI is enabled through `anstyle-query`/`anstyle-wincon`
  (legacy consoles get native colour calls; Windows Terminal and
  ConPTY get VT). A console that refuses VT mode falls back to no colour
  and no redraw. Unicode glyphs (spinner braille, box lines) fall back
  to ASCII (`|/-\`, `-`) on legacy code pages and when `FROB_ASCII` is set.
- Width changes: the widgets re-read the size on every redraw (and on
  SIGWINCH where available); a bar never exceeds `width - 1` columns, and
  when `width < 40` it collapses to `stage n/m elapsed`.
- Dumb or unknown width: plain lines, no truncation tricks.
- Output text is ASCII in this repository; the optional glyphs are
  runtime-selected and live in the palette module, one table, with the
  ASCII fallback beside each.

## 4. Palette

Semantic roles, not colours, are the API (`Style` is `anstyle::Style`):

| Role | Use | Default |
|---|---|---|
| `ok` | passed gate, closed ticket | green |
| `warn` | warning finding, stale lease | yellow |
| `error` | error finding, refusal | bold red |
| `info` | stage name, verb heading | bold cyan |
| `dim` | elapsed time, secondary ids, paths | bright black |
| `id` | ticket and rule ids | bold |
| `accent` | the changed/selected row, current stage | magenta |

Colours use the 16 ANSI colours only, so terminal themes decide the
shades and no truecolor probing is needed. A single `Palette::plain()`
(all `Style::new()`) is what a no-colour stream gets: callers never
branch on colour themselves, they render with the palette they are
given. Severity maps to roles one-to-one with diagnostics.md severities.

## 5. Presenter trait and event model

```rust
pub trait Presenter: Send + Sync {
    /// A stage began; `total` is the known step count when there is one.
    fn stage_start(&self, stage: &StageId, total: Option<u64>);
    /// Progress inside the current stage (monotonic).
    fn stage_progress(&self, stage: &StageId, done: u64);
    /// A stage finished with its measured duration and outcome.
    fn stage_end(&self, stage: &StageId, elapsed: Duration, outcome: Outcome);
    /// Print a human line above any live widget (through the log layer).
    fn line(&self, role: Role, text: &str);
    /// Called once at verb exit; renders the profile report if enabled.
    fn finish(&self, report: &ProfileReport);
}
```

Implementations: `Quiet` (no output), `Plain` (one line per event, used
for CI, dumb terminals and piped stderr), `Live` (ratatui inline
viewport: a bar when `total` is known, a spinner otherwise, plus the
completed-stage list). Selection is a pure function of `Capabilities`.

`StageEvent` is the data form emitted by producers as `tracing` events
(target `frob::stage`, fields `stage`, `phase = start|progress|end`,
`done`, `total`, `elapsed_ms`, `outcome`, `ui = true`). Producers never
hold a `Presenter`: they emit events, the `PresentLayer` translates them.
This keeps frob-land and frob-check free of any terminal dependency and
makes the same events usable for the JSON log (`--json` log lines) and
for the telemetry file.

`StageId` is a stable dotted name (`land.merge`, `check.rules`,
`check.tests`); the set is versioned with the verb docs, and an unknown
stage is displayed verbatim.

`ProfileReport` is built from the end events: per-stage elapsed, share of
total, the slowest stage flagged `warn` above a configurable share.
It is printed at exit with `--profile` (or `[ui] profile = true`), is
included in the envelope under `data.profile` only when requested (an
additive field, so the default envelope is unchanged), and is always
written to the telemetry file when that is enabled.

Elapsed time comes from the injected `Clock` (time.md); the presenter
never reads the wall clock.

## 6. Routing all output through logging

1. Human lines are `tracing` events with `ui = true` and a `role`
   field; `Presenter::line` is the only function that turns them into
   bytes on a terminal.
2. Final verb results: the dispatcher (gob-cli) renders the envelope to
   the text view or JSON and writes it to stdout through one function,
   `emit_result`, the single place that owns stdout. Verb code returns
   data and never writes.
3. Redaction runs on the event text before styling (gob-log `redact`).
4. The `println`-family ban is enforced by workspace clippy deny
   (~J1PTXPF); the grimble rule for all languages is ~JKKJPTT.
   `frob-present` and `emit_result` are the two allowed writers.

## 7. Follow-up tickets and their dependency on this design

| Ticket | Builds | Depends on this file for |
|---|---|---|
| ~VXR58J9 | `frob-present`: `Palette`, `Capabilities`, `Presenter` impls, bar and spinner | sections 2 to 5 verbatim; no verb wiring |
| ~MCY59H4 | `StageEvent` emission from frob-land and frob-check, `ProfileReport` | section 5 event fields and `StageId` names; needs the `PresentLayer` type only through events, so it can land before the widgets |
| ~W1GQTPG | tables, status lines and error layout for every verb's text view | section 4 roles and section 6 rule 2; needs ~VXR58J9 |
| ~4270F1C | route remaining human output through logging, ban `println` in verb code | section 6; coordinates with ~J1PTXPF |

Order: ~VXR58J9 and ~MCY59H4 are independent and can run in parallel
(the event field names above are the only shared surface); ~W1GQTPG and
~4270F1C follow ~VXR58J9.

## 8. Tests

- `Capabilities::detect` is table-tested over the section 3 matrix with
  an injected environment (TTY/no TTY, `NO_COLOR`, `TERM=dumb`, `CI`,
  forced colour, Windows legacy console fake).
- `Plain` and `Quiet` presenters are snapshot-tested on a buffer; `Live`
  is tested against ratatui's `TestBackend` at several widths including
  a mid-run resize.
- A pipe test runs `frob check --json` with stderr as a pty and asserts
  stdout is byte-identical to the non-TTY run and contains no `\x1b`.
- Every verb's `--text` output with `NO_COLOR=1` contains no escape
  byte.
