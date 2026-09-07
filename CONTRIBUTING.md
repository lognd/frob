# Contributing to frob

Thanks for considering a contribution. This document has two paths
through it: a short summary if you already know how open-source
contribution works, and a full walkthrough if this is your first time.
Read whichever one applies; both point at the same commands.

## TL;DR for experienced contributors

- Fork the repo, clone your fork, add `lognd/frob` as `upstream`.
- `uv sync --extra serve` installs frob plus its dev dependency group.
  Inside this checkout specifically, always invoke `uv run frob`, never a
  bare `frob` -- a globally `uv tool install`-ed frob can drift from this
  checkout's own source, and `frob` itself warns about exactly this
  ("CLI-surface skew risk").
- `uv run frob doctor` confirms the native extensions (`frob-core`,
  `strata-core`) built; `uv run frob natives build` builds them if not.
- `uv run frob check` is the gate: ruff, ty, cycle/dup/arch/bind/exports,
  and every other enforcement gate, in one pass. Green here before you
  open a PR.
- `uv run frob test --base main` runs exactly the tests touched by your
  diff; `uv run frob test --all` runs the whole suite.
- Commit format: `<type>(<scope>): <imperative summary, 72 chars max>`.
  Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`,
  `ci`, `build`. No trailing period. One logical change per commit.
- ASCII only in every file, no exceptions, no emoji.
- Every public symbol gets a one-line docstring (WHY/WHAT, not a
  restatement of the name).
- Every fallible operation a caller must handle returns a typani
  `Result[T, E]`; exceptions are for programmer bugs, not expected
  failure.
- Work is tracked in the `tickets/` directory via `frob ticket`, not in
  a side channel -- see "How this repo is enforced: frob" below for the
  full ticket-queue workflow this project actually uses.
- Fill in every box of `.github/PULL_REQUEST_TEMPLATE.md`; an unchecked
  box with no explanation will slow down review.

## Your first contribution (step by step)

If you have never opened a pull request against someone else's project
before, this section is for you. None of the steps below are specific to
frob; they are the standard GitHub flow, spelled out.

### 1. Fork the repository

A "fork" is your own copy of the project on GitHub, which you can push
to freely without needing write access to the original. Open
[github.com/lognd/frob](https://github.com/lognd/frob) and click "Fork"
in the top right.

### 2. Clone your fork

```bash
git clone https://github.com/<your-username>/frob.git
cd frob
git remote add upstream https://github.com/lognd/frob.git
```

The `upstream` remote lets you pull in changes from the real project
later (`git fetch upstream`).

### 3. Install uv

frob uses [uv](https://docs.astral.sh/uv/) for dependency management and
running commands. Install it following the instructions at
[docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/).
You do not need to install Python separately; uv manages that too.

### 4. Install dependencies

```bash
uv sync --extra serve
uv run frob natives build
```

This creates a `.venv`, installs frob itself plus its dev dependency
group, and builds the two optional native extensions (`frob-core`,
`strata-core`). frob works without the natives too, in pure-Python mode
-- see docs/guides/install.md.

### 5. Run the tests once, to see green

```bash
uv run frob test --all
```

Everything should pass on a clean checkout. If it does not, something is
wrong with your environment, not with your (not-yet-written) change --
worth checking before you go further.

### 6. Pick a ticket

```bash
uv run frob ticket doable
```

This lists tickets with no unmet blockers, ordered by priority. Pick one
that looks like a good first change -- something small and narrowly
scoped is much easier to review, and much more likely to be accepted,
than a sweeping change. `uv run frob ticket show T-####` prints the
ticket's full body: its Description, its Plan, and its declared `scope`
(the file/symbol globs your change is allowed to touch).

```bash
uv run frob ticket start T-####
```

`start` moves the ticket to `in-progress` and runs a pre-work sweep
(duplicate/cross-reference check over the declared scope) before you
write a line of code.

### 7. Make your change, inside the declared scope

Touch only files and symbols matching the ticket's `scope`. As you add or
change a public symbol, bind it to the ticket and its tests with comment
directives (see "The directive DSL" below) and add a one-line docstring.
If you find work that needs doing but falls outside the ticket's scope --
a bug in a neighboring module, a stale doc you don't own -- do not fix it
silently and do not expand scope yourself; file a new ticket instead:

```bash
uv run frob ticket new --title "..." --kind bug --scope "..." \
    --body "found while working T-####"
```

### 8. Run the local gate

```bash
uv run frob check --ticket T-####
```

This checks scope, pre-work, drift, coverage, and test-binding gates,
scoped to your ticket. `uv run frob test --base main` runs exactly the
tests your diff touches.

### 9. Bind evidence, write the Done report, close the ticket

Close a ticket in this exact order -- doing it out of order produces a
Done report with a wrong or missing evidence count:

```bash
uv run frob ticket evidence T-#### <test-node-id> [...]
```

Then write the Done report in the ticket body (`Changed`, `Evidence`,
`Filed`, `Gates` sections -- see "The Done report" below for the exact
shape), and only then:

```bash
uv run frob ticket close T-####
```

`close` re-verifies the evidence and the Done report; it is not a
formality you can skip by editing the ticket file directly.

### 10. Commit your change

```bash
git add path/to/changed_file.py
git commit -m "fix(gates): correct off-by-one in scope matching"
```

See the [commit format](#tldr-for-experienced-contributors) above. Small,
focused commits are easier to review than one giant commit at the end.

### 11. Push a branch and open the PR

```bash
git checkout -b fix/scope-off-by-one
git push -u origin fix/scope-off-by-one
```

Then open a pull request from your fork's branch against `lognd/frob`'s
`main` branch on GitHub. Fill in `.github/PULL_REQUEST_TEMPLATE.md`
completely -- it appears automatically when you open the PR.

### 12. What review looks like

A maintainer will read the diff, run the gate, and either approve,
request changes, or ask questions in the PR thread. Expect comments even
on a good change -- that is normal review, not a sign something is
wrong. Push additional commits to the same branch to address feedback;
no need to open a new PR.

### 13. If CI is red

Click through to the failing check and read the log; it will point at
the failing test, lint rule, or gate. Fix it locally, re-run
`uv run frob check`, and push again. If the failure looks unrelated to
your change (flaky test, infrastructure issue), say so in the PR thread
rather than guessing at a fix.

## What makes a good change

- **Small scope.** One logical change per PR, matching one ticket's
  declared `scope`. A PR that touches the gate engine, the ticket ledger,
  and the release script at once is very hard to review and very easy to
  get wrong.
- **A test that fails before and passes after.** If you cannot write
  such a test, it is worth asking whether the change is well specified
  yet.
- **Docs updated in the same change.** If the change touches a
  documented symbol, update the matching page under `docs/` and keep its
  `frob:doc` anchor comment pointed at the right symbol in the same
  commit, not a follow-up.
- **No new dependencies without discussion.** Open an issue first if you
  think frob needs one.

## How this repo is enforced: frob

frob enforces itself. `uv run frob check` is the actual merge gate, and
CI runs it on every push and pull request (see `.github/workflows/ci.yml`).
You do not need frob installed to *propose* a change, but a PR that does
not pass `uv run frob check` will not be merged.

### The directive DSL

| Directive | Meaning | What to do as a contributor |
|-----------|---------|------------------------------|
| `# frob:ticket T-0042` | This code is accounted for by ticket T-0042. | Add it above every public symbol you add or change. |
| `# frob:tests path::symbol` | This test is bound as evidence for the given source symbol. | Add it above every test that covers a public function you touch. |
| `# frob:doc docs/x.md#anchor` | This symbol is described at that doc anchor; the gate fails if the doc drifts out of sync. | Keep it pointed at the right anchor if you move or rename the symbol; update the doc in the same commit. |
| `# frob:invariant INV-007` | A claimed property (idempotent, always terminates, etc.) with a bound proof obligation. | Only add one you can back with a real test; ask in the PR if unsure. |
| `# frob:todo T-0042 note` | A deliberately deferred piece of work, tracked against an open ticket. | Never write a bare `# TODO` in this repo -- `frob check` fails it (TODO001). If you have no ticket id yet, file one first. |
| `# frob:waive RULE-ID reason="..."` | An explicit, visible exception to a gate rule, with a stated reason. | Do not add one yourself unless you understand the rule being waived; ask in the PR if you think one is needed. |

### The ticket queue

Work lives under the `tickets/` directory, one file per ticket, tracked
in git, not in a side channel that can silently fall out of sync with
the code. Each ticket has a `state` (`queued`, `planned`, `in-progress`,
`done`, `blocked`, `dropped`), a declared `scope` of file/symbol globs,
and (once closed) bound evidence and a Done report. `uv run frob ticket
doable`, `show`, `start`, `evidence`, `done-report`, and `close` are the
commands you will use most -- see step 6-9 above for the exact sequence,
or docs/modules/tickets.md and docs/modules/tickets-lifecycle.md for the
full reference.

### The Done report

Every closed ticket carries a Done report in its body:

```markdown
## Done report

Changed: <symrefs touched, one per line>
Evidence: <pytest node ids / policy rule ids bound via frob:tests>
Filed: <any new ticket ids opened for out-of-scope discoveries, or "none">
Gates: frob check --ticket T-#### clean (or: waived RULE-ID at file:line, reason)
```

`frob ticket close` refuses to close a ticket with empty evidence or a
missing Done report.

## AI-assisted contributions

AI-assisted contributions are welcome under the following policy, which
is deliberately strict. The rules exist so that AI assistance moves work
off reviewers rather than onto them: a generated diff nobody has read is
review work transferred to the maintainer, not a contribution.

**(a) Disclosure.** Say in the PR description which tool you used and
roughly how (drafted the initial patch, reviewed and edited an
AI-drafted patch, wrote tests with AI assistance, and so on). The PR
template has a line for this; fill it in honestly.

**(b) You are the author.** You are responsible for every line, whether
you or a model typed it. You must be able to explain any part of the
diff if asked in review. "The model said so" is not an acceptable answer
to a review question -- if you cannot explain why a line is there, it
should not be in the PR yet.

**(c) Not accepted:**

- An unreviewed, unedited AI-generated PR submitted as-is.
- A PR description that was clearly not written for this specific repo
  (generic boilerplate, wrong project name, invented capabilities).
- A bulk or sweeping change with no prior issue or ticket discussing it.
- Generated tests that only assert the current behavior of the code
  (a test that would pass on a buggy implementation just as easily as a
  correct one is not a test).

**(d) If you are an AI agent working in this repository:**

These are the house rules an agent must follow here, written directly to
the agent, not to whoever is dispatching it.

- Run `uv run frob check` (and `uv run frob test --base main`) before
  claiming a task is done. A gate you did not run is not a gate you can
  claim passed.
- Use `frob ticket doable` to find work, `frob ticket start` to claim a
  ticket, and stay strictly inside that ticket's declared `scope`. Close
  a ticket in the exact order from step 9 above: bind evidence first,
  then write the Done report, then close.
- Never touch a file or symbol outside the declared scope. File a new
  ticket instead of expanding scope on your own.
- Keep every `frob:` directive you encounter intact. Add matching
  directives (`frob:ticket`, `frob:tests`, `frob:doc`) on new public
  symbols you introduce, following the nearest existing example.
- Never leave a bare `# TODO`. Use `# frob:todo T-#### note` bound to an
  open ticket.
- Every fallible operation returns a typani `Result`; raise exceptions
  only for programmer bugs, never for expected failure paths.
- ASCII only, in every file you touch, no exceptions, no emoji.
- Never read or write `.env` files, directly or indirectly.
- Never amend a commit that has already been pushed; create a new
  commit instead.
- Follow the commit format above exactly. Never add a `Co-Authored-By`
  trailer or any other attribution line to a commit message.
- Report honestly. If a gate is red, say so in the PR or the task
  report -- do not narrow the scope of what you claim to have done
  without saying that you did.
- An agent-authored PR still needs a named human contributor who takes
  authorship responsibility for it, per (b) above. An agent does not
  merge its own PR.

## Reporting bugs and proposing features

Use the issue forms:

- [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)

## License

By contributing to frob, you agree that your contributions are licensed
under the project's GPL-2.0-only license (see [LICENSE](LICENSE)).
