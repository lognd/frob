# Prose remedies in refusals

Status: proposed
Owner: frob
Decisions: D79
Audience: contributor

Ticket: ~M7ZJQJT (child of the remedy-quality epic). Scope: `frob-land`,
`frob-worktree`, `frob-lease` callers of `Refusal::with_remedy`.

## Problem

`gob-diagnostics::Refusal` carries `remedy` (text), `command`
(`RemedyCommand`, structured) and `requires_human`. `with_command` sets both
`command` and `remedy` (the rendering), overwriting any earlier text. So a
refusal today is either prose only, or a bare command with no explanation.
Several sites need both: why, then the command. Today they cram the command
into prose (unrunnable by agents) or lose the prose.

Concrete bug shape: `frob-lease/src/verbs.rs` `ActorMismatch` calls
`with_remedy("... with the command below ...")` then `with_command(..)`; the
second call replaces the prose, so "the command below" is never shown.

## Design

Add one field and one builder to `Refusal` (and `EnvelopeError`, schema bump
additive):

- `note: Option<String>`: prose that explains or qualifies the remedy.
- `Refusal::with_note(impl Into<String>)`: sets `note`; independent of
  `with_command`/`with_remedy`, so call order no longer matters.

Rules:

1. `command` present: `remedy` is its rendering, `note` is optional context.
   Text output prints `note` then `remedy`.
2. No runnable command exists (human action, file edit): use `with_remedy`
   prose plus `requiring_human()` when only a person can act; otherwise
   prose-only is allowed when the fix is an edit to a named file.
3. Never embed a command inside prose when it can be a `RemedyCommand`.
4. `with_remedy` keeps its meaning (exact corrected command as text) and is
   not deprecated; it simply stops being the vehicle for explanations.

## Site classification

Convert (command exists; keep prose as `note`):

| Site | Command |
| --- | --- |
| lease `ActorMismatch` | `frob work <t> --steal --reason` (fixes lost-prose bug) |
| lease `Queued` | `frob work <t> --wait <secs>` |
| worktree `work.rs` claim-lost | `frob work <other>`; or `frob work <t> --anyway --reason <why>` |
| worktree `cycle_gate` overdue | `frob cycle close --retro <text>` |
| worktree `cycle_gate` not-in-cycle | `frob cycle assign <t>`; alt `frob work <t> --unplanned --reason` as `note` |
| worktree `wip` repo/expedite | per-case: `frob lease list` / `frob requeue <t>` |
| land `train_close` / `land` dirty checkout | `git stash` (product `git`) then `frob land <t>` |
| land `E-LAND-GIT-REV` | `git branch --list` |

Stay prose (edit a file or wait; no single runnable command):

| Site | Why |
| --- | --- |
| lease lockfile overlap | edit `[lease] shared_files` in `frob.toml` |
| lease `Format` | rename a corrupt file |
| `E-CONFIG` in land and worktree | fix `frob.toml` as described |
| `claim_evict` window / precondition / rerun-later | wait; nothing to run |

For the stay-prose group, set `requiring_human()` only where an agent cannot
make the edit safely (none of the above qualify; agents may edit `frob.toml`).

## Rollout

1. gob-diagnostics: add `note`, `with_note`, envelope field, schema, tests,
   text rendering (`note` line before the remedy line). One ticket.
2. Convert the "Convert" table, one ticket per crate (disjoint scopes), each
   asserting the structured `command` in tests.
3. Leave the "Stay prose" group untouched.

## Acceptance

Every remaining text-only `with_remedy` site in the three crates appears in
exactly one table above.
