# frob docs

frob is the enforcement layer for agentic development: an obligation graph,
a statically-checkable ticket queue, and gates that turn unaccounted-for
work into a `frob check` failure. Start with `docs/rework.md` for the
architecture, then `docs/quickstart.md` to see the enforcement loop run for
real.

## Architecture overview

- `docs/rework.md` -- the identity, the module dependency graph, the alpha
  purge (what was deleted and why), the agents/skills redesign, and the
  cross-cutting design decisions. Read this first.

## Getting started

- `docs/quickstart.md` -- a real end-to-end walkthrough: build the graph,
  file a ticket, annotate code, hit a violation, fix it, ack, test, close.
- `docs/agentic-workflow.md` -- the human/AI split: how planner, implementer,
  reviewer, prover, and the auditors use the ticket queue and gates as the
  shared work surface, including the worktree-per-agent pattern.

## Module design docs

The four components that make up the enforcement layer:

- `docs/graph.md` -- `frob.graph`: the obligation graph engine, the comment
  DSL (`frob:ticket`, `frob:tests`, `frob:doc`, `frob:invariant`,
  `frob:waive`, ...), digests, the lock file, and drift.
- `docs/tickets.md` -- `frob.tickets`: the ticket/feature queue, its state
  machine, attachments, and clipboard capture.
- `docs/gates.md` -- `frob.gates`: the drift, coverage, scope, pre-work,
  invariant, test, and policy gates; the rule catalog; invariants; and
  `frob check` integration.
- `docs/testing.md` -- `frob.testing`: touched-set selection across the diff,
  the per-language runner registry, and worktree-correct git semantics via
  `frob.gitio`.
- `docs/perf.md` -- `frob.perf`: profiling (`frob perf profile`), symbol-
  level heat-maps (`frob perf heat`), and the PERF001..PERF004 linear-scan
  gates.

Two modules that support the above but are not yet fully re-platformed:

- `docs/lang.md` -- `frob.lang`: the tree-sitter parsing core (symbols +
  comments, five languages) that `frob.graph` is built on.
- `docs/dup.md` -- `frob.dup`: duplicate/clone detection, including the
  0.2.0 smart-dup design (region-granular semantic clones, DUP001/DUP002
  gates).
- `docs/fuzz.md` -- `frob.fuzz`: the 0.2.0 enforced property fuzzing design
  (Arbitrary protocol, FUZZ gates).
- `docs/vet.md` -- policy/vetting notes referenced by `frob.gates`.

## Per-command references

Kept commands, each with usage, real output, and a "why it exists" section:

| Doc | Command |
|---|---|
| `docs/scaffold.md` | `frob scaffold` |
| `docs/cycle.md` | `frob cycle` |
| `docs/outline.md` | `frob outline` |
| `docs/map.md` | `frob map` |
| `docs/xref.md` | `frob xref` |
| `docs/exports.md` | `frob exports` |
| `docs/parse.md` | `frob parse` |
| `docs/gitlog.md` | `frob gitlog` |
| `docs/check.md` | `frob check` |

`frob graph`, `frob ack`, `frob ticket`, and `frob test` are documented in
their owning module design docs above (`docs/graph.md`, `docs/tickets.md`,
`docs/testing.md`) rather than as separate per-command pages, since their
usage is inseparable from the data model they operate on.

## Planned / tracked work

- `TODO.md` -- the dispatchable checklist: phase status, deferred items
  (`frob ticket renumber`, mutation testing, `frob serve`), and anything
  recorded as explicitly cut scope.
