# Diagnostics that teach, and fixes that are safe to apply

Status: current
Owner: gob
Decisions: D78
Audience: contributor

Provenance: ACCEPTED with changes (D78, owner review 2026-10-04, ticket
~J8PJHKX). The changes: first-occurrence teaching is on by default and
a long explanation can always be repeated (section 5.1); `--fix` stays
within the current ticket's scope (section 3).
Applies to frob, grimble and crunk alike (gob-diagnostics, gob-rules,
gob-cli). Modelled on rustc and cargo: the compiler teaches the language
while you use it, every error has a code you can look up, and fixes are
labelled by how safe they are to apply.

## 1. Principles

1. Every message answers three questions: what is wrong (one sentence),
   where (a source snippet with the span underlined), and what to do
   (a concrete next step, not a lecture).
2. A message never makes the user search. Each finding names its rule
   id and slug and ends with `= help: run grimble explain SYS001` (or
   `frob explain`), which prints the full rule page offline, generated
   from the same source as the web reference (as `rustc --explain E0308`
   prints the error index entry).
3. The tool teaches the next step at every point a newcomer can get
   stuck: an empty repository, a missing config, a missing model root,
   a missing ledger branch, an unknown verb, a typo in a key. Each of
   those is a diagnostic with a remedy, never a bare failure.
4. Teaching is not noise: help lines appear in text mode; JSON carries
   the same content as fields (`remedy`, `explain`, `fixes`) for agents.
   `--quiet` drops help lines; nothing is ever printed only to "be nice".

## 2. Message shape

```text
error[SYS003]: unit claimed by two bindings that disagree
  --> crates/frob-check/src/lib.rs:42:1
   |
42 | pub fn run(root: &Path) -> Report {
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ bound to node `frob` by a grimble:binds directive
   |
  ::: design/model.grmb:12:3
   |
12 |   owns "crates/frob-check/**" ;
   |   ---------------------------- also owned by node `checks` through this selector
   |
   = note: a directive outranks a selector, so `frob` is the owner today
   = help: remove the directive, or narrow the selector to exclude this file
   = fix (needs review): narrow the selector to "crates/frob-check/src/*.rs" except lib.rs
   = explain: grimble explain SYS003
```

Security rules for all rendered text (security.md 2.10, D82): every
text field carries an `origin` (`host`, `std`, `pack:NAME`, `source`,
`tracker`, `ledger`) and non-host text is labelled; controls, bidi and
invisible characters are always escaped; `remedy`, `help` and fix
commands come only from host templates; first-occurrence teaching
applies to std rules only; plugin fixes are at most `maybe-incorrect`
unless the pack holds `fix.machine`, and never touch the control plane.

Rules for the renderer (gob-diagnostics): primary span with a label;
secondary spans in other files with `:::` headers; `note` for facts the
user did not ask for but needs; `help` for the next action; `fix` lines
only when a machine fix exists, with its applicability (section 3);
colour only on a terminal (`NO_COLOR` respected); every line ASCII.

## 3. Fix applicability (rustc's model)

Each `Fix` on a finding carries one applicability. The existing
`FixKind` (Manual, Deterministic, VerifyCommit, FixIt) maps onto it.

| Applicability | Meaning | Auto-applied? | Example |
|---|---|---|---|
| `machine` | Provably preserves meaning; idempotent; touches only the finding's span or a generated file | yes, with `--fix` | expand an abbreviated ticket id to its full ULID; sort `owns` clauses (fmt); regenerate a stale generated doc; materialize a missing config knob with its default |
| `maybe-incorrect` | Usually right, may change meaning | never automatically; offered | narrow a selector; add a grant for an observed capability |
| `has-placeholders` | Needs input the tool cannot know | never; shown as a template | add an excuse template with `because = "<reason>"` |
| `manual` | No machine fix; the help line describes the steps | no | split a function that owns logic it dispatches |

`--fix` applies only `machine` fixes, re-runs the affected rules once,
and reports what it changed and what remains (as `cargo fix` and ruff
do). It stays within scope: inside a ticket worktree it edits only files
in the ticket's scope (plus generated files the scope owns) and lists
the out-of-scope fixes it skipped, with the command that would widen the
scope (`frob lease widen`). Outside a ticket it edits only the paths the
check was asked to cover. `--fix --unsafe` is not offered in version 1: a fix that may be
wrong is reviewed by a person, not by a flag.

## 4. Auto-apply and prompting: when, and when never

- **Never silently.** A plain `check` changes nothing. Ever. Writing
  files requires `--fix` (or the `fix` verb).
- **Machine fixes with `--fix`** are applied without asking, because they
  are proven safe and reversible with version control. The run prints a
  summary and the exact files changed.
- **Interactive review on a terminal**: `frob fix --interactive` (and
  `grimble fix --interactive`) walks through `maybe-incorrect` fixes one
  at a time with a diff and `[y]es / [n]o / [e]dit / [s]kip rule / [q]uit`.
  Only when stdin and stdout are a TTY; otherwise it refuses with exit 2
  and tells the caller to use the JSON fix list instead.
- **Never prompt unasked.** A check run on a terminal does not stop to
  ask questions: prompts inside non-interactive verbs break scripts,
  hooks, CI and agents, and are the first thing users disable. Instead
  the summary ends with one line: `3 fixes available (1 safe): run frob
  check --fix, or frob fix --interactive to review the rest`.
- **Agents** read `fixes` from the JSON envelope (each with its
  applicability and the exact text edits) and apply them through their
  own tools, so the agent path never depends on a TTY.

So: auto-apply is good for the narrow, provable class; prompting is
good only inside an explicitly interactive verb; prompting during a
normal run is a bad idea.

## 5. Teaching moments (built in from day one)

| Situation | What the user sees |
|---|---|
| first run in a repository without `frob.toml` or `grimble.toml` | what the tool is in two sentences, the one command to initialize, and what it will write |
| ledger branch missing in a clone | `note: tickets live on the branch frob-tickets`; `help: git fetch origin frob-tickets` (one command), and a pointer to the branch README |
| unknown verb or flag | did-you-mean (strsim) plus the three most likely verbs |
| unknown config key | did-you-mean against the materialized table, and the doc link for the table |
| no model root declared (MDL021) | the default root path, and `grimble init` if the file is missing |
| a finding seen for the first time in this repository | the full `explain` text inline once (on by default, `[ui] teach = "first"`), then only the one-line help afterwards (state kept in `.frob/seen.toml`, local and disposable) |
| Unresolved finding | why the tool could not decide (the reason code in words) and the exact annotation or capability that would let it decide |

### 5.1 Repeating a long explanation

Teaching once must never mean losing the text. Every path back to it is
one command, and the one-line help after the first occurrence names it:

| Want | Command |
|---|---|
| one rule's full explanation again | `frob explain SYS003` / `grimble explain SYS003` (any time, offline) |
| the full explanation for every finding in this run | `frob check --teach` (alias `--explain-all`) |
| the explanation for findings of one rule in this run | `frob check --teach SYS003` |
| start over as if new | `frob teach reset` (or `reset SYS003`), which edits `.frob/seen.toml` |
| never inline, help lines only | `[ui] teach = "never"`; `"always"` prints in full every time |

The one-line form after the first occurrence is
`= explain: grimble explain SYS003 (shown in full on first occurrence)`,
so a reader who scrolled past it knows it exists and how to get it.
Long explanations go through the pager on a TTY (`$PAGER`, then `less
-R`), and print plainly otherwise.

## 6. Where explanations come from

Each rule's explanation is its doc comment (`#[derive(Rule)]`) or its
pack rule's `explain` text; gob-dev generates the web reference from the
same source (docs/reference/rules/<ID>.md) and the binaries embed it for
`explain`. One source, three outputs (terminal, web, JSON), so they can
never disagree. GEN001 keeps the generated copies current.

## 7. Owner decisions (2026-10-04)

1. First-occurrence inline teaching is on by default, with the repeat
   paths of section 5.1.
2. `--fix` stays within the current ticket's scope (section 3).
