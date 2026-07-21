# Agentic workflow

How the human and a fleet of agents share one work surface: the ticket
queue, gated by `frob check`. Nothing is done until it is a closed ticket
with evidence; nothing escapes review because the gates are mechanical, not
a matter of an agent remembering to ask.

---

## The human/AI split

The human's job is to queue outcomes, not implementation steps:

<!-- frob:describes src/frob/__main__.py::_add_ticket_new_parser -->
<!-- frob:describes src/frob/__main__.py::_add_ticket_attach_and_lifecycle_end_parsers -->
```bash
frob ticket new --title "..." --kind feature --body "..."
frob ticket attach T-0040        # paste a clipboard mockup, if stdin is a TTY
```

`frob ticket new`/`attach` offer clipboard paste only interactively; agents
and CI always pass explicit file paths (see `docs/modules/tickets.md`).

Everything downstream -- decomposition, implementation, review, proof -- is
an agent's job, dispatched through the roles below and defined in
`agents/*/SKILL.md`.

---

## The roles

| Role | Agent | Reads | Writes |
|---|---|---|---|
| Decompose a goal into work | `agents/planner` | the goal, `frob ticket list` | ticket tree (`parent`/`blocked_by`) |
| Implement one ticket | `agents/implementer` | the ticket, its scope | code, directives, Done report |
| Verify a Done report | `agents/reviewer` | diff, evidence, gate output | a verdict (APPROVE/REJECT) -- never fixes |
| Close invariant gaps | `agents/prover` | `frob check --only invariant` | property tests, policy rules, evidence lists |
| Audit one module boundary | `agents/interface-auditor` | one package's public API | tickets only |
| Run a security sweep | `agents/security-auditor` | the repo/subtree | policy rules + invariants + tickets, always all three |
| Fix one failing test | `agents/debugger` | the error, the target function | a fix, or a `frob ticket fail` entry |

No agent holds private state. The ticket queue, `frob.lock`, `invariants/`,
and `frob.toml` policy are the only durable memory; a mission that doesn't
write to one of those did not happen, as far as the next session is
concerned.

---

## skills/plan: goal -> ticket tree

<!-- frob:describes src/frob/__main__.py::_add_map_parser -->
<!-- frob:describes src/frob/__main__.py::_add_ticket_query_parsers -->
```bash
frob map src/
frob ticket list                 # don't replan what's already queued
```

`skills/plan` orients (without reading source files), resolves design risks
before decomposition locks in scope, then dispatches `agents/planner`. The
planner never implements -- it emits `frob ticket new` calls with
`parent`/`blocked_by` edges and a narrow `scope` per leaf, and ends with the
full list of ticket ids it created. If a leaf ticket's scope is `src/**`,
it isn't decomposed; split it further.

---

## skills/next: the work loop

<!-- frob:describes src/frob/__main__.py::_add_ticket_query_parsers -->
```bash
frob ticket doable                # ordered, unblocked, oldest-first
```

`skills/next` is the loop that pops one ticket, dispatches `implementer`,
dispatches `reviewer` against the same ticket id, and either closes
(APPROVE) or hands the reviewer's findings back to a fresh `implementer`
dispatch (REJECT). It re-queries `frob ticket doable` every pass, since
closing one ticket can unblock others. It never implements directly and
never closes over a REJECT.

### implementer: pre-work gate, scope, evidence

```bash
frob ticket start T-0042          # pre-work sweep: dup + xref over scope
# implement strictly within scope; add frob:ticket / frob:tests directives
frob check --ticket T-0042        # scope/pre-work/drift/coverage/test gates
frob ticket close T-0042          # requires non-empty evidence + Done report
```

Anything found outside the ticket's declared `scope` is filed as a new
ticket, never folded into the current diff:

<!-- frob:describes src/frob/__main__.py::_add_ticket_new_parser -->
```bash
frob ticket new --title "..." --kind bug --scope "..." --body "found while working T-0042"
```

### reviewer: verifying the done-report

The reviewer re-runs `frob check --ticket T-0042`, reads the actual diff
against the claimed scope, opens every evidence test node id, and confirms
docs that carry a `doc` edge were genuinely updated (not rubber-stamp
`frob ack`s). One failed checklist item is REJECT -- see `agents/reviewer`
for the full six-point checklist. The reviewer never fixes and never calls
`frob ticket close` itself; its verdict is the only output.

---

## skills/audit: interface + security sweeps

<!-- frob:describes src/frob/__main__.py::_add_map_parser -->
<!-- frob:describes src/frob/__main__.py::_add_check_parser -->
```bash
frob map src/                     # enumerate package boundaries
frob check --only test             # TEST003 already flags known interfaces
```

One `interface-auditor` mission per package boundary (never repo-wide in a
single mission -- that produces shallow findings), plus one repo-wide
`security-auditor` mission. Both are report-only: every finding becomes a
ticket, and every security finding additionally produces a policy rule (or
tree-sitter query) and an `invariants/INV-###.md` entry, so a fix without a
rule that would have caught it recurring is treated as half-done.

---

## skills/prove: closing invariant gaps

<!-- frob:describes src/frob/__main__.py::_add_check_parser -->
```bash
frob check --only invariant       # INV001 (no evidence) / INV002 (no anchor)
```

`agents/prover` anchors missing `frob:invariant` comments and writes
property tests (hypothesis-style where the property is a "for all inputs"
claim) or policy rules as evidence, looping until `frob check --only
invariant` is clean. It never implements missing enforcement code itself --
that's a `kind: invariant` ticket for `implementer` to pick up.

---

## `frob check` as the gate every agent must pass

Every agent's contract ends the same way: `frob check` (scoped to the
active ticket via `--ticket`, or the relevant `--only` stage) must be clean,
or every remaining violation must carry a reasoned
`frob:waive RULE-ID reason="..."`. A ticket closed with failing gates is
worse than one left open -- it defeats the reason the queue exists.

`frob test --base main` is the executable counterpart: `frob check` proves
the test bindings exist (`TEST001`-`TEST006`), `frob test` runs exactly the
touched-set tests those bindings declare, before any Done report is
written.

---

## Worktree-per-agent

Dispatching multiple agents in parallel means one git worktree per agent,
each on its own branch:

```bash
git worktree add ../frob-t0042 -b T-0042-clipboard-attach
```

This is a first-class target, not an afterthought (see `docs/modules/testing.md`
"Git worktrees"):

- **`frob.gitio` is the one git subprocess seam**, and `repo_root` resolves
  via `git rev-parse --show-toplevel`, which is correct from inside a linked
  worktree -- frob never touches `.git` internals directly.
- **`.frob/` is per-worktree, never shared.** The graph cache, the pre-work
  sweep, and the pytest-collection cache all live at each worktree's own
  root; sharing them across checkouts of different commits would poison
  incremental hashing. This falls straight out of `.frob/` being gitignored
  and always rebuildable.
- **Base semantics are branch-relative.** `frob test`/`frob check` diff
  against `merge-base(HEAD, base)`, so in an agent's worktree the touched
  set is exactly that agent's own delta -- the same command means "test my
  changes" whether run in the main checkout or any worktree.
- **Tracked truth merges like code.** Tickets, invariants, `frob.lock`, and
  comment directives are ordinary tracked files; worktree branches carry
  their own view and merge through git like any other change. The one known
  seam: two worktrees can allocate the same sequential ticket id
  concurrently -- `frob ticket list` surfaces the collision as
  `DuplicateId` post-merge; the structural fix (collision-proof allocation
  plus a first-class `frob ticket renumber`) is tracked as ticket T-0162.

---

## BLOCKER handling

If `implementer` or `debugger` returns a BLOCKER (the fix is structural,
would mask a recurring bug, or requires a public API change it isn't
authorized to make): do not patch around it. Read the blocker, check
whether other agents are hitting the same root cause, resolve the
structural problem first (a fresh ticket, possibly `kind: invariant` if it
implies a property that must hold), then reissue the original ticket.
