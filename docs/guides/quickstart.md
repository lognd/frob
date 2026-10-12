# Quickstart: from `frob init` to a landed ticket

Status: current
Owner: frob
Decisions: none
Audience: user

Tutorial (Diataxis: learning). You will take one change through the whole frob
loop in a throwaway repository: init, plan, lease, change, test, bind evidence,
check, land, and look at the board and the release status. It takes about ten
minutes and needs `git`, `frob` ([install](../../README.md#install)) and
`cargo` with `cargo-nextest` (the example is a tiny Rust crate; frob also runs
pytest, vitest and jest, and `frob doctor --text` lists what it found).

Every command block below marked `sh` is run against a real repository by the
test `crates/frob/tests/doc_commands.rs`, so it stays true. Handles such as
`~Q5FEE2P` are generated per ticket; in your repository, use the one
`frob ticket new` prints.

## Words you need

- **Ticket**: one unit of work, stored under `tickets/` in git. Its **handle**
  (`~Q5FEE2P`) is a short alias of its 26-character ULID; either works wherever
  a ticket is named.
- **Category**: where a ticket is on the board: triage, todo, in-progress,
  done. A done ticket carries an outcome.
- **Scope and lease**: the file globs a ticket may change. `frob work` takes
  a lease on them; no other ticket can lease an overlapping glob.
- **Acceptance criteria and evidence**: a criterion is a "given, when, then"
  sentence. Evidence is a measurement (a test run) bound to a criterion with
  `--accepts N`. A ticket cannot close with an unbound criterion.
- **Ledger**: tickets, cycles and milestones are event files committed to the
  base branch by frob itself (commits titled `tickets(...)`); do not edit them
  by hand.

## 1. Make a repository

```sh
mkdir demo && cd demo
git init -b main
mkdir src
printf '[package]\nname = "calc"\nversion = "0.1.0"\nedition = "2021"\n' > Cargo.toml
printf 'pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n' > src/lib.rs
printf 'target/\n.frob/\n' > .gitignore
cargo generate-lockfile
git add -A && git commit -m "init"
```

## 2. Initialise frob

```sh
frob init
git add -A && git commit -m "chore: frob init"
```

`init` is safe to repeat. It writes `frob.toml` with every knob at its default,
a `.gitattributes` line for the ledger merge driver, and an ignore for the
`.frob/` cache. Commit all of it. `frob doctor` reports toolchain, git, config
and ledger health at any time.

The base branch (`main` here) is detected; `frob check` compares against it.

## 3. Plan: a cycle and a ticket

A cycle is a time box with a capacity in story points. Create one that contains
today, then a ticket with a scope, points and one acceptance criterion:

```sh
frob cycle new --start 2026-10-08 --end 2026-10-15 --goal "first cycle" --capacity 8
frob ticket new --title "Add multiply" --scope 'src/**' --points 2 \
    --acceptance "Given two numbers, when mul runs, then it returns their product"
```

Note the handle in the output (here `~Q5FEE2P`). Put the ticket in the cycle:

```sh
frob cycle assign ~Q5FEE2P
frob ticket list
```

Do not put `changelog.d/**` in a scope; fragments are always allowed.

## 4. Lease the ticket and make the change

```sh
frob work ~Q5FEE2P
```

`work` creates a branch `ticket/Q5FEE2P` and a worktree, by default in a
sibling directory `../<repo>-wt/Q5FEE2P` (set `[worktree] dir` in `frob.toml`
to move it; a sandboxed editor that may only write inside the project cannot
use the default). The JSON output names the path. Move there; the ticket is now
in-progress and its scope is leased:

```sh
cd ../demo-wt/Q5FEE2P
printf '\npub fn mul(a: i32, b: i32) -> i32 {\n    a * b\n}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn mul_multiplies() {\n        assert_eq!(super::mul(2, 3), 6);\n    }\n}\n' >> src/lib.rs
git add -A && git commit -m "feat(calc): add mul"
```

Editing a file outside the leased globs makes `frob check --ticket` fail with
SCOPE001; widen the lease with `frob ticket update ~Q5FEE2P --add-scope GLOB`.

## 5. Run only the tests the change reaches

```sh
frob test --base main
```

`test` maps the files changed since the base to the tests that reach them, runs
exactly those, and records the run as evidence on the ticket. It does not
choose which criterion the run proves; you bind that next. Tests run from the
repository root, so a Rust crate in a subdirectory needs a `Cargo.toml`
workspace at the root. A python project works the same way with pytest.

## 6. Bind evidence to the criterion

```sh
frob ticket evidence add ~Q5FEE2P --provider command --ref "cargo test" --accepts 1
frob ticket show ~Q5FEE2P --format md
```

`--accepts 1` binds the measurement to criterion 1. The `md` view lists
the criteria as `[bound]` or `[unbound]`. Other providers are `nextest`,
`pytest`, `vitest`, `jest`, `dotnet`, `file` and `attestation`. `command` runs a tool
named in `[evidence] allowed_tools` (by default `cargo`, `git`, `pytest`, `vitest`, `jest` and `dotnet`; `python3` is not).

## 7. Add the changelog fragment and check

The default definition of done (`[pm] done_requires`) wants a changelog
fragment per ticket (rule REL003):

```sh
frob ticket fragment ~Q5FEE2P
git add -A && git commit -m "docs: changelog fragment"
frob check --ticket ~Q5FEE2P
```

`check --ticket` limits the report to what this ticket's diff introduced. A
fresh repository also shows a few advisory or "unresolved" lines (frob's own
files have no language adapter; `PM033` says the ready queue is short). They do
not fail the gate: exit 0 passes, 1 means findings at or above `fail_on`, 2 is
a usage error, 3 is a refusal, 4 is an internal error.

## 8. Land

Back in the primary checkout:

```sh
cd ../../demo
frob land ~Q5FEE2P
```

`land` re-checks the ticket against the base, merges the branch, closes the
ticket as done, removes the worktree and commits the ledger. It refuses, with
a remedy command, when a criterion is unbound, the check is red, the worktree
is dirty or the fragment is missing. `--dry-run` shows the plan.

## 9. Look around

```sh
frob board
frob cycle show
frob cycle velocity
frob release status
```

`board` shows the columns with WIP limits (default two in progress) and card
ages. `cycle close` carries unfinished work to the next cycle and records the
ratio; after three closed cycles `velocity` gives the capacity `cycle assign`
uses. `release status` reports readiness of a milestone: create one with
`frob milestone new <VERSION> --goal <text> --criterion <text>`, add an epic
with `frob milestone add <EPIC> <VERSION>` and cut with `frob release cut`.
`release cut` bumps Cargo versions only, so it fits Rust workspaces; for
frob's own release see [release.md](release.md).

## When something is refused

Errors carry a code, the cause and a remedy command, for example
`E-DONE-CRITERIA-UNBOUND` prints the exact `frob ticket evidence add ...` to
run. `frob check --explain RULE` prints a rule's page (the same pages are in
[../reference/rules/](../reference/rules/)).

## Where next

- [../reference/cli/frob.md](../reference/cli/frob.md): every verb and flag.
- [../reference/config.md](../reference/config.md): every `frob.toml` key.
- [upgrade-from-v1.md](upgrade-from-v1.md): command map from v1 and ticket import.
